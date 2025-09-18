"""
Google Sheets Organization System
Manages RFP lifecycle, status updates, color coding, and archival
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

logger = logging.getLogger(__name__)

class SheetOrganizer:
    """Manages RFP organization, status updates, and archival"""
    
    # Status definitions
    STATUS_NEW = "New"
    STATUS_ACTIVE = "Active"
    STATUS_EXPIRING = "Expiring"
    STATUS_EXPIRED = "Expired"
    STATUS_COMPLETED = "Completed"
    STATUS_SUBMITTED = "Submitted"  # Treat as completed for archival
    
    # Color definitions (RGB 0-1 scale for Google Sheets API)
    COLORS = {
        'red': {'red': 1.0, 'green': 0.2, 'blue': 0.2},
        'green': {'red': 0.2, 'green': 0.8, 'blue': 0.2},
        'yellow': {'red': 1.0, 'green': 1.0, 'blue': 0.0},
        'lime': {'red': 0.0, 'green': 1.0, 'blue': 0.0},
        'cyan': {'red': 0.0, 'green': 1.0, 'blue': 1.0},
        'pink': {'red': 1.0, 'green': 0.75, 'blue': 0.8},
        'white': {'red': 1.0, 'green': 1.0, 'blue': 1.0}
    }
    
    # Score labels and colors
    SCORE_CONFIG = {
        7: {'label': 'Medium', 'color': 'yellow'},
        8: {'label': 'High', 'color': 'lime'},
        9: {'label': 'Excellent', 'color': 'cyan'},
        10: {'label': 'Perfect', 'color': 'pink'}
    }
    
    def __init__(self, credentials_path: str):
        """Initialize the organizer with Google Sheets credentials"""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=self.credentials)
        except Exception as e:
            logger.error(f"Failed to initialize SheetOrganizer: {str(e)}")
            raise
    
    def calculate_status(self, posted_date: str, deadline: str, current_status: str) -> str:
        """
        Calculate the appropriate status based on dates
        
        Args:
            posted_date: Date when RFP was posted (YYYY-MM-DD format)
            deadline: Response deadline (YYYY-MM-DD or ISO format)
            current_status: Current status value
            
        Returns:
            New status string
        """
        # If manually marked as completed or submitted, keep it
        if current_status in [self.STATUS_COMPLETED, self.STATUS_SUBMITTED]:
            return current_status
        
        try:
            # Parse dates
            today = datetime.now().date()
            
            # Parse posted date
            if posted_date:
                if 'T' in posted_date:
                    posted = datetime.fromisoformat(posted_date.replace('Z', '+00:00')).date()
                else:
                    posted = datetime.strptime(posted_date, '%Y-%m-%d').date()
                days_since_posted = (today - posted).days
            else:
                days_since_posted = 0
            
            # Parse deadline
            if deadline:
                if 'T' in deadline:
                    # ISO format with time
                    deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00')).date()
                else:
                    # Simple date format
                    deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                days_until_deadline = (deadline_date - today).days
            else:
                # No deadline, treat as active
                return self.STATUS_ACTIVE if days_since_posted >= 3 else self.STATUS_NEW
            
            # Determine status based on rules
            if days_until_deadline < 0:
                return self.STATUS_EXPIRED
            elif days_until_deadline < 3:
                return self.STATUS_EXPIRING
            elif days_since_posted >= 3:
                return self.STATUS_ACTIVE
            else:
                return self.STATUS_NEW
                
        except Exception as e:
            logger.warning(f"Error calculating status: {str(e)}")
            return current_status  # Keep current if calculation fails
    
    def get_all_rfps(self, sheet_id: str) -> List[Dict]:
        """
        Get all RFPs from a sheet with their current data
        
        Returns:
            List of RFP dictionaries with row numbers and data
        """
        try:
            # Get all data from the sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A:T'  # Get columns A through T (all standard columns)
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:
                return []  # No data beyond headers
            
            headers = values[0]
            rfps = []
            
            # Find column indices
            col_indices = {}
            for i, header in enumerate(headers):
                col_indices[header] = i
            
            # Process each row
            for row_num, row in enumerate(values[1:], start=2):
                # Pad row to ensure all columns exist
                while len(row) < len(headers):
                    row.append('')
                
                rfp = {
                    'row_number': row_num,
                    'status': row[col_indices.get('Status', 2)] if 'Status' in col_indices else '',
                    'posted_date': row[col_indices.get('Posted Date', 10)] if 'Posted Date' in col_indices else '',
                    'deadline': row[col_indices.get('Response Deadline', 3)] if 'Response Deadline' in col_indices else '',
                    'notice_id': row[col_indices.get('Notice ID', 4)] if 'Notice ID' in col_indices else '',
                    'title': row[col_indices.get('Title', 6)] if 'Title' in col_indices else '',
                    'ai_score': row[col_indices.get('AI Score', 13)] if 'AI Score' in col_indices else '',
                    'date_added': row[col_indices.get('Date Added', 18)] if 'Date Added' in col_indices else '',
                    'full_row': row
                }
                rfps.append(rfp)
            
            return rfps
            
        except Exception as e:
            logger.error(f"Error getting RFPs from sheet: {str(e)}")
            return []
    
    def update_rfp_statuses(self, sheet_id: str) -> Dict[str, int]:
        """
        Update all RFP statuses based on date rules
        
        Returns:
            Dictionary with counts of status changes
        """
        stats = {
            'updated': 0,
            'new_to_active': 0,
            'active_to_expiring': 0,
            'expiring_to_expired': 0,
            'total_processed': 0
        }
        
        try:
            rfps = self.get_all_rfps(sheet_id)
            stats['total_processed'] = len(rfps)
            
            batch_updates = []
            
            for rfp in rfps:
                old_status = rfp['status']
                new_status = self.calculate_status(
                    rfp['posted_date'],
                    rfp['deadline'],
                    old_status
                )
                
                if old_status != new_status:
                    # Queue status update
                    batch_updates.append({
                        'range': f'C{rfp["row_number"]}',  # Status column
                        'values': [[new_status]]
                    })
                    
                    # Track changes
                    stats['updated'] += 1
                    if old_status == self.STATUS_NEW and new_status == self.STATUS_ACTIVE:
                        stats['new_to_active'] += 1
                    elif old_status == self.STATUS_ACTIVE and new_status == self.STATUS_EXPIRING:
                        stats['active_to_expiring'] += 1
                    elif new_status == self.STATUS_EXPIRED:
                        stats['expiring_to_expired'] += 1
            
            # Apply batch updates
            if batch_updates:
                self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={
                        'valueInputOption': 'USER_ENTERED',
                        'data': batch_updates
                    }
                ).execute()
                
                logger.info(f"Updated {stats['updated']} RFP statuses")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error updating statuses: {str(e)}")
            return stats
    
    def apply_status_colors(self, sheet_id: str):
        """Apply color coding based on status"""
        try:
            rfps = self.get_all_rfps(sheet_id)
            
            # Prepare batch formatting requests
            requests = []
            
            for rfp in rfps:
                row_idx = rfp['row_number'] - 1  # 0-based for API
                status = rfp['status']
                
                # Determine color based on status
                bg_color = None
                if status == self.STATUS_EXPIRED:
                    bg_color = self.COLORS['red']
                elif status in [self.STATUS_COMPLETED, self.STATUS_SUBMITTED]:
                    bg_color = self.COLORS['green']
                else:
                    bg_color = self.COLORS['white']  # Default/clear
                
                if bg_color:
                    # Apply to columns A-C (indices 0-2)
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': 0,
                                'startRowIndex': row_idx,
                                'endRowIndex': row_idx + 1,
                                'startColumnIndex': 0,
                                'endColumnIndex': 3
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': bg_color
                                }
                            },
                            'fields': 'userEnteredFormat.backgroundColor'
                        }
                    })
            
            # Apply batch formatting
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={'requests': requests}
                ).execute()
                
                logger.info(f"Applied status colors to {len(requests)} rows")
                
        except Exception as e:
            logger.error(f"Error applying status colors: {str(e)}")
    
    def apply_score_colors_and_labels(self, sheet_id: str):
        """Apply color coding and labels to AI scores in column N"""
        try:
            rfps = self.get_all_rfps(sheet_id)
            
            batch_updates = []
            format_requests = []
            
            for rfp in rfps:
                try:
                    score = int(float(rfp['ai_score'])) if rfp['ai_score'] else 0
                    
                    if score in self.SCORE_CONFIG:
                        config = self.SCORE_CONFIG[score]
                        row_idx = rfp['row_number'] - 1  # 0-based
                        
                        # Update cell value with label only
                        batch_updates.append({
                            'range': f'N{rfp["row_number"]}',  # AI Score column
                            'values': [[config["label"]]]
                        })
                        
                        # Apply background color
                        format_requests.append({
                            'repeatCell': {
                                'range': {
                                    'sheetId': 0,
                                    'startRowIndex': row_idx,
                                    'endRowIndex': row_idx + 1,
                                    'startColumnIndex': 13,  # Column N
                                    'endColumnIndex': 14
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': self.COLORS[config['color']],
                                        'horizontalAlignment': 'CENTER',
                                        'textFormat': {'bold': True}
                                    }
                                },
                                'fields': 'userEnteredFormat.backgroundColor,userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.bold'
                            }
                        })
                except (ValueError, TypeError):
                    continue  # Skip invalid scores
            
            # Apply value updates
            if batch_updates:
                self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={
                        'valueInputOption': 'USER_ENTERED',
                        'data': batch_updates
                    }
                ).execute()
            
            # Apply formatting
            if format_requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={'requests': format_requests}
                ).execute()
                
                logger.info(f"Applied score colors and labels to {len(format_requests)} cells")
                
        except Exception as e:
            logger.error(f"Error applying score colors: {str(e)}")
    
    def archive_old_rfps(self, source_sheet_id: str, graveyard_sheet_id: str, 
                        bank_sheet_id: str, days_after_deadline: int = 7) -> Dict[str, int]:
        """
        Archive old RFPs to Graveyard (expired) or Bank (completed)
        
        Args:
            source_sheet_id: Main sheet to archive from
            graveyard_sheet_id: Sheet for expired RFPs
            bank_sheet_id: Sheet for completed RFPs
            days_after_deadline: Days to wait after deadline/completion before archiving
            
        Returns:
            Statistics on archived RFPs
        """
        stats = {'to_graveyard': 0, 'to_bank': 0}
        
        try:
            rfps = self.get_all_rfps(source_sheet_id)
            today = datetime.now().date()
            
            rows_to_delete = []
            graveyard_rows = []
            bank_rows = []
            
            for rfp in rfps:
                should_archive = False
                target = None
                
                # Check if should be archived
                if rfp['status'] == self.STATUS_EXPIRED:
                    # Check if expired long enough
                    if rfp['deadline']:
                        try:
                            if 'T' in rfp['deadline']:
                                deadline = datetime.fromisoformat(rfp['deadline'].replace('Z', '+00:00')).date()
                            else:
                                deadline = datetime.strptime(rfp['deadline'], '%Y-%m-%d').date()
                            
                            days_past = (today - deadline).days
                            if days_past >= days_after_deadline:
                                should_archive = True
                                target = 'graveyard'
                                graveyard_rows.append(rfp['full_row'])
                                stats['to_graveyard'] += 1
                        except:
                            pass
                            
                elif rfp['status'] in [self.STATUS_COMPLETED, self.STATUS_SUBMITTED]:
                    # Check completion date (use date_added as proxy)
                    if rfp['date_added']:
                        try:
                            # Assume completed recently if status is completed/submitted
                            # In production, you'd track actual completion date
                            should_archive = True
                            target = 'bank'
                            bank_rows.append(rfp['full_row'])
                            stats['to_bank'] += 1
                        except:
                            pass
                
                if should_archive:
                    rows_to_delete.append(rfp['row_number'])
            
            # Add to archive sheets
            if graveyard_rows and graveyard_sheet_id:
                self._append_to_sheet(graveyard_sheet_id, graveyard_rows)
                logger.info(f"Archived {len(graveyard_rows)} RFPs to Graveyard")
            
            if bank_rows and bank_sheet_id:
                self._append_to_sheet(bank_sheet_id, bank_rows)
                logger.info(f"Archived {len(bank_rows)} RFPs to Bank")
            
            # Delete from source sheet (in reverse order to maintain row numbers)
            if rows_to_delete:
                for row_num in sorted(rows_to_delete, reverse=True):
                    self._delete_row(source_sheet_id, row_num)
                    time.sleep(0.5)  # Rate limiting
            
            return stats
            
        except Exception as e:
            logger.error(f"Error archiving RFPs: {str(e)}")
            return stats
    
    def _append_to_sheet(self, sheet_id: str, rows: List[List]):
        """Append rows to a sheet"""
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='A:T',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': rows}
            ).execute()
        except Exception as e:
            logger.error(f"Error appending to sheet: {str(e)}")
    
    def _delete_row(self, sheet_id: str, row_number: int):
        """Delete a specific row from a sheet"""
        try:
            requests = [{
                'deleteDimension': {
                    'range': {
                        'sheetId': 0,
                        'dimension': 'ROWS',
                        'startIndex': row_number - 1,  # 0-based
                        'endIndex': row_number
                    }
                }
            }]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            ).execute()
        except Exception as e:
            logger.error(f"Error deleting row {row_number}: {str(e)}")
    
    def create_archive_sheet(self, title: str) -> Optional[str]:
        """Create a new archive sheet with proper headers"""
        try:
            # Create new spreadsheet
            spreadsheet_body = {
                'properties': {'title': title},
                'sheets': [{
                    'properties': {
                        'title': 'Archive',
                        'gridProperties': {'frozenRowCount': 1}
                    }
                }]
            }
            
            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()
            
            sheet_id = spreadsheet.get('spreadsheetId')
            
            # Add headers (same as main sheet)
            headers = [[
                'AI Recommended',
                'Human Review',
                'Status',
                'Response Deadline',
                'Notice ID',
                'Solicitation Number',
                'Title',
                'Agency',
                'NAICS',
                'PSC',
                'Posted Date',
                'SAM.gov Link',
                'Drive Folder',
                'AI Score',
                'AI Justification',
                'Key Requirements',
                'Suggested Approach',
                'AI Application',
                'Date Added',
                'Date Archived'  # Extra column for archive date
            ]]
            
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='A1:U1',
                valueInputOption='USER_ENTERED',
                body={'values': headers}
            ).execute()
            
            logger.info(f"Created archive sheet: {title} with ID: {sheet_id}")
            return sheet_id
            
        except Exception as e:
            logger.error(f"Error creating archive sheet: {str(e)}")
            return None
    
    def run_full_maintenance(self, main_sheet_id: str, maybe_sheet_id: str = None,
                            graveyard_sheet_id: str = None, bank_sheet_id: str = None) -> Dict:
        """
        Run complete maintenance routine on sheets
        
        Returns:
            Summary statistics of all operations
        """
        summary = {
            'statuses_updated': 0,
            'colors_applied': 0,
            'archived_to_graveyard': 0,
            'archived_to_bank': 0,
            'errors': []
        }
        
        try:
            # Update statuses
            logger.info("Updating RFP statuses...")
            status_stats = self.update_rfp_statuses(main_sheet_id)
            summary['statuses_updated'] = status_stats['updated']
            
            # Apply status colors
            logger.info("Applying status colors...")
            self.apply_status_colors(main_sheet_id)
            summary['colors_applied'] += 1
            
            # Apply score colors and labels
            logger.info("Applying score colors and labels...")
            self.apply_score_colors_and_labels(main_sheet_id)
            
            # Also process maybe sheet if provided
            if maybe_sheet_id:
                self.update_rfp_statuses(maybe_sheet_id)
                self.apply_status_colors(maybe_sheet_id)
                self.apply_score_colors_and_labels(maybe_sheet_id)
                summary['colors_applied'] += 1
            
            # Archive old RFPs
            if graveyard_sheet_id or bank_sheet_id:
                logger.info("Archiving old RFPs...")
                archive_stats = self.archive_old_rfps(
                    main_sheet_id, 
                    graveyard_sheet_id, 
                    bank_sheet_id
                )
                summary['archived_to_graveyard'] = archive_stats['to_graveyard']
                summary['archived_to_bank'] = archive_stats['to_bank']
            
            logger.info(f"Maintenance complete: {summary}")
            
        except Exception as e:
            error_msg = f"Error in maintenance: {str(e)}"
            logger.error(error_msg)
            summary['errors'].append(error_msg)
        
        return summary