import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import ssl
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Retry decorator for SSL and network errors
@retry(
    stop=stop_after_attempt(5),  # Try up to 5 times
    wait=wait_exponential(multiplier=2, min=4, max=60),  # Wait 4s, 8s, 16s, 32s, 60s
    retry=retry_if_exception_type((ssl.SSLError, ConnectionError, TimeoutError, HttpError))
)
def execute_with_retry(request):
    """Execute a Google API request with retry logic for network errors"""
    return request.execute()

class SheetsManager:
    def __init__(self, service_account_path: str):
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            )
            self.service = build('sheets', 'v4', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            raise
    
    def create_or_get_sheet(self, title: str, spreadsheet_id: str = None) -> str:
        """Create a new sheet or use existing one if ID provided"""
        
        if spreadsheet_id:
            try:
                # Verify the sheet exists and we have access
                self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                logger.info(f"Using existing sheet: {spreadsheet_id}")
                
                # Try to add headers if the sheet is empty
                try:
                    self._setup_headers_if_needed(spreadsheet_id)
                except:
                    logger.info("Headers may already exist or cannot be added")
                
                return spreadsheet_id
            except HttpError as e:
                logger.warning(f"Could not access sheet {spreadsheet_id}: {str(e)}")
                # Return the ID anyway - we'll try to use it
                return spreadsheet_id
        
        # Create new spreadsheet (this will fail without Sheets API)
        spreadsheet_body = {
            'properties': {'title': title},
            'sheets': [{
                'properties': {
                    'title': 'Opportunities',
                    'gridProperties': {
                        'frozenRowCount': 1
                    }
                }
            }]
        }
        
        try:
            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()
            
            sheet_id = spreadsheet.get('spreadsheetId')
            
            # Add headers
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
                'Info Doc',
                'Date Added'
            ]]
            
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='Opportunities!A1:T1',
                valueInputOption='USER_ENTERED',
                body={'values': headers}
            ).execute()
            
            # Apply formatting
            self._format_sheet(sheet_id, spreadsheet['sheets'][0]['properties']['sheetId'])
            
            # Make it accessible (optional - you might want to share with specific emails)
            self._share_sheet(sheet_id)
            
            logger.info(f"Created new sheet: {title} with ID: {sheet_id}")
            return sheet_id
            
        except Exception as e:
            logger.error(f"Failed to create sheet: {str(e)}")
            raise
    
    def _setup_headers_if_needed(self, sheet_id: str):
        """Add headers to sheet if it's empty"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:T1'
            ).execute()
            
            if not result.get('values'):
                # Sheet is empty, add headers
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
                    'Info Doc',
                    'Date Added'
                ]]
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range='A1:T1',
                    valueInputOption='USER_ENTERED',
                    body={'values': headers}
                ).execute()
                logger.info("Added headers to sheet")
        except:
            pass
    
    def get_existing_notice_ids(self, sheet_id: str) -> set:
        """Get all existing Notice IDs from a sheet to check for duplicates"""
        try:
            # Try to read Notice ID column (usually column E or similar)
            # First, try to find which column has Notice IDs
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Sheet1!A1:Z1'  # Get headers
            ).execute()
            
            headers = result.get('values', [[]])[0]
            notice_id_col = None
            
            # Find the Notice ID column
            for i, header in enumerate(headers):
                if 'notice' in header.lower() and 'id' in header.lower():
                    # Convert column index to letter (0=A, 1=B, etc.)
                    notice_id_col = chr(65 + i)
                    break
            
            if not notice_id_col:
                # Default to column E if not found
                notice_id_col = 'E'
            
            # Now get all values from that column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f'Sheet1!{notice_id_col}:{notice_id_col}'
            ).execute()
            
            values = result.get('values', [])
            # Skip header row and extract Notice IDs
            notice_ids = set()
            for row in values[1:]:  # Skip header
                if row and row[0]:  # If there's a value
                    notice_ids.add(str(row[0]).strip())
            
            logger.info(f"Found {len(notice_ids)} existing Notice IDs in sheet {sheet_id}")
            return notice_ids
            
        except Exception as e:
            logger.warning(f"Could not read existing Notice IDs from {sheet_id}: {str(e)}")
            return set()
    
    def get_existing_universal_ids(self, sheet_id: str) -> set:
        """Get all Universal IDs (PLATFORM:ID) from a sheet for multi-platform duplicate detection"""
        try:
            # Get headers to find Platform and Platform ID columns
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Sheet1!A1:Z1'
            ).execute()
            
            headers = result.get('values', [[]])[0]
            platform_col = None
            platform_id_col = None
            
            # Find columns
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'platform' in header_lower and 'id' not in header_lower:
                    platform_col = chr(65 + i)
                elif 'platform' in header_lower and 'id' in header_lower:
                    platform_id_col = chr(65 + i)
                elif 'notice' in header_lower and 'id' in header_lower and not platform_id_col:
                    # Fallback to Notice ID if Platform ID not found
                    platform_id_col = chr(65 + i)
            
            if not platform_col or not platform_id_col:
                # Fall back to legacy Notice ID only
                return self.get_existing_notice_ids(sheet_id)
            
            # Get both columns
            range_str = f'Sheet1!{platform_col}:{platform_id_col}'
            if ord(platform_id_col) < ord(platform_col):
                range_str = f'Sheet1!{platform_id_col}:{platform_col}'
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_str
            ).execute()
            
            values = result.get('values', [])
            universal_ids = set()
            
            for row in values[1:]:  # Skip header
                if len(row) >= 2:
                    platform = row[0] if ord(platform_col) < ord(platform_id_col) else row[1]
                    platform_id = row[1] if ord(platform_col) < ord(platform_id_col) else row[0]
                    
                    if platform and platform_id:
                        # Create universal ID
                        universal_id = f"{platform}:{platform_id}"
                        universal_ids.add(universal_id)
                elif len(row) == 1 and row[0]:
                    # Legacy format - assume SAM
                    universal_ids.add(f"SAM:{row[0]}")
            
            logger.info(f"Found {len(universal_ids)} existing Universal IDs in sheet {sheet_id}")
            return universal_ids
            
        except Exception as e:
            logger.warning(f"Could not read Universal IDs from {sheet_id}: {str(e)}")
            return set()
    
    def get_existing_content_hashes(self, sheet_id: str) -> set:
        """Get all content hashes for cross-platform duplicate detection"""
        try:
            # Get headers to find Content Hash column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Sheet1!A1:Z1'
            ).execute()
            
            headers = result.get('values', [[]])[0]
            hash_col = None
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'content' in header_lower and 'hash' in header_lower:
                    hash_col = chr(65 + i)
                    break
            
            if not hash_col:
                return set()  # No content hash column yet
            
            # Get content hash column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f'Sheet1!{hash_col}:{hash_col}'
            ).execute()
            
            values = result.get('values', [])
            content_hashes = set()
            
            for row in values[1:]:  # Skip header
                if row and row[0]:
                    content_hashes.add(str(row[0]).strip())
            
            logger.info(f"Found {len(content_hashes)} existing content hashes in sheet {sheet_id}")
            return content_hashes
            
        except Exception as e:
            logger.warning(f"Could not read content hashes from {sheet_id}: {str(e)}")
            return set()
    
    def setup_multiplatform_headers(self, sheet_id: str):
        """Setup headers for multi-platform RFP tracking in Main/Maybe sheets"""
        try:
            # Check if headers exist and need updating
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:Z1'
            ).execute()
            
            existing_headers = result.get('values', [[]])[0] if result.get('values') else []
            
            # Check if platform columns already exist
            has_platform = any('platform' in h.lower() for h in existing_headers)
            
            if not has_platform and existing_headers:
                # Add new platform columns after existing ones
                logger.info(f"Adding platform columns to sheet {sheet_id}")
                # This would need to insert new columns - for now we'll just log
                logger.info("Note: Manual column addition may be needed for platform support")
            
        except Exception as e:
            logger.warning(f"Could not update headers in {sheet_id}: {str(e)}")
    
    def _calculate_status(self, posted_date: str, deadline: str) -> str:
        """Calculate RFP status based on dates"""
        try:
            today = datetime.now().date()
            
            # Parse deadline
            if deadline:
                if 'T' in deadline:
                    deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00')).date()
                else:
                    deadline_date = datetime.strptime(deadline[:10], '%Y-%m-%d').date()
                
                days_until_deadline = (deadline_date - today).days
                
                if days_until_deadline < 0:
                    return 'Expired'
                elif days_until_deadline < 3:
                    return 'Expiring'
            
            # Parse posted date
            if posted_date:
                if 'T' in posted_date:
                    posted = datetime.fromisoformat(posted_date.replace('Z', '+00:00')).date()
                else:
                    posted = datetime.strptime(posted_date[:10], '%Y-%m-%d').date()
                
                days_since_posted = (today - posted).days
                
                if days_since_posted >= 3:
                    return 'Active'
            
            return 'New'
            
        except Exception as e:
            logger.warning(f"Error calculating status: {str(e)}")
            return 'New'
    
    def _get_score_label(self, score: int, is_imported: bool = False) -> str:
        """Get label and color for AI score"""
        if is_imported:
            return 'Imported'
        score_config = {
            7: 'Medium',
            8: 'High',
            9: 'Excellent',
            10: 'Perfect'
        }
        return score_config.get(score, str(score))
    
    def add_opportunity(self, sheet_id: str, opportunity: Dict, assessment: Dict, folder_url: str, info_doc_link: str = None):
        """Add opportunity to tracking sheet with optional info doc link"""
        
        # Calculate status based on dates
        status = self._calculate_status(
            opportunity.get('postedDate', ''),
            opportunity.get('responseDeadLine', '')
        )
        
        # Get score label
        score = assessment.get('relevance_score', 0)
        is_imported = assessment.get('is_imported', False)
        score_display = self._get_score_label(score, is_imported) if is_imported or score >= 7 else str(score)
        
        # Prepare row data with checkboxes
        row_data = [[
            '✓' if assessment.get('is_qualified', False) else '✗',  # AI Recommended
            '',  # Human Review (blank for manual checkbox)
            status,  # Calculated Status
            opportunity.get('responseDeadLine', ''),  # Response Deadline
            opportunity.get('noticeId', ''),  # Notice ID
            opportunity.get('solicitationNumber', ''),  # Solicitation Number
            opportunity.get('title', '')[:200],  # Title (truncated)
            opportunity.get('fullParentPathName', ''),  # Agency
            opportunity.get('naicsCode', ''),  # NAICS
            opportunity.get('classificationCode', ''),  # PSC
            opportunity.get('postedDate', ''),  # Posted Date
            f'=HYPERLINK("{opportunity.get("uiLink", "")}", "{opportunity.get("uiLink", "")}")',  # SAM.gov Link
            f'=HYPERLINK("{folder_url}", "Open Folder")',  # Drive Folder
            score_display,  # AI Score with label
            assessment.get('justification', ''),  # AI Justification
            ', '.join(assessment.get('key_requirements', [])),  # Key Requirements
            assessment.get('suggested_approach', ''),  # Suggested Approach
            assessment.get('ai_application', ''),  # AI Application
            f'=HYPERLINK("{info_doc_link}", "Full Info")' if info_doc_link else '',  # Info Doc
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Date Added
        ]]
        
        try:
            # Get current row count with retry
            request = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Sheet1!A:A'
            )
            result = execute_with_retry(request)
            
            next_row = len(result.get('values', [])) + 1
            
            # Append data with retry
            request = self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f'Sheet1!A{next_row}:T{next_row}',
                valueInputOption='USER_ENTERED',
                body={'values': row_data}
            )
            execute_with_retry(request)
            
            # Add checkbox formatting for Human Review column
            self._add_checkbox(sheet_id, next_row, 2)  # Column B
            
            # Add dropdown for Status column
            self._add_status_dropdown(sheet_id, next_row, 3)  # Column C
            
            # Apply color formatting based on status
            self._apply_status_colors(sheet_id, next_row, status)
            
            # Apply score color formatting
            if is_imported:
                self._apply_imported_color(sheet_id, next_row)
            elif score >= 7:
                self._apply_score_color(sheet_id, next_row, score)
            
            logger.info(f"Added opportunity {opportunity.get('noticeId')} to row {next_row} with status '{status}' and score '{score_display}'")
            
        except Exception as e:
            logger.error(f"Failed to add opportunity to sheet: {str(e)}")
            raise
    
    def get_all_notice_ids(self, sheet_id: str) -> List[str]:
        """Get all notice IDs from sheet for deduplication"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Sheet1!E:E'  # Notice ID column
            ).execute()
            
            values = result.get('values', [])
            # Skip header row
            notice_ids = [row[0] for row in values[1:] if row and row[0]]
            
            logger.info(f"Retrieved {len(notice_ids)} existing notice IDs")
            return notice_ids
            
        except Exception as e:
            logger.error(f"Error getting notice IDs: {str(e)}")
            return []
    
    def add_to_spam_sheet(self, sheet_id: str, opportunity: Dict, assessment: Dict, platform: str = 'SAM'):
        """Add ALL evaluated opportunities to spam sheet with multi-platform support"""
        from sanitizer import Sanitizer
        
        # Extract platform-specific ID based on platform
        if platform == 'SAM':
            platform_id = opportunity.get('noticeId', '')
        elif platform == 'SIBR':
            platform_id = opportunity.get('rfp_id', '') or opportunity.get('solicitation_id', '')
        elif platform == 'VULCAN':
            platform_id = opportunity.get('opportunity_number', '') or opportunity.get('opp_id', '')
        else:
            platform_id = opportunity.get('id', '') or opportunity.get('noticeId', '')
        
        # Create universal ID and content hash
        universal_id = f"{platform.upper()}:{platform_id}"
        
        # Generate content hash for cross-platform detection
        import hashlib
        fingerprint = f"{opportunity.get('title', '').lower().strip()[:100]}"
        fingerprint += f"{opportunity.get('fullParentPathName', '').lower().strip()}"
        fingerprint += f"{opportunity.get('postedDate', '')[:10]}"
        content_hash = hashlib.md5(fingerprint.encode()).hexdigest()[:16]
        
        # Sanitize all data before writing to sheets
        title = Sanitizer.sanitize_for_sheets(opportunity.get('title', ''))
        agency = Sanitizer.sanitize_for_sheets(opportunity.get('fullParentPathName', ''))
        justification = Sanitizer.sanitize_for_sheets(assessment.get('justification', ''))
        ai_application = Sanitizer.sanitize_for_sheets(assessment.get('ai_application', ''))
        
        # Get score label for display
        score = assessment.get('relevance_score', 0)
        score_display = self._get_score_label(score) if score >= 7 else str(score)
        
        # Build row with platform information - match enhanced_discovery.py schema
        row_data = [[
            score_display,  # AI Score with label
            '✅' if assessment.get('is_qualified', False) else '🤔' if assessment.get('relevance_score', 0) >= 4 else '❌',  # Status emoji
            title[:200],  # Title
            agency[:100],  # Agency
            opportunity.get('type', ''),  # Type
            opportunity.get('naicsCode', ''),  # NAICS
            opportunity.get('postedDate', ''),  # Posted Date
            opportunity.get('responseDeadLine', ''),  # Deadline
            justification[:500],  # Justification
            ai_application[:300] if ai_application else '',  # AI Application
            ', '.join(assessment.get('similar_past_rfps', [])[:2]) if assessment.get('similar_past_rfps') else '',  # Similar RFPs
            f'=HYPERLINK("{opportunity.get("uiLink", "")}", "{opportunity.get("uiLink", "")}")',  # Link
            opportunity.get('noticeId', ''),  # Notice ID
            datetime.now().strftime('%Y-%m-%d %H:%M')  # Evaluated Date (shorter format)
        ]]
        
        try:
            # Append to spam sheet with retry logic for SSL/network errors
            request = self.service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='A:N',  # Match the schema used in enhanced_discovery.py
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': row_data}
            )
            execute_with_retry(request)
            
            logger.info(f"Added {opportunity.get('noticeId')} to spam sheet with score {assessment.get('relevance_score')}")
            
        except Exception as e:
            logger.error(f"Failed to add to spam sheet after retries: {str(e)}")
            # Re-raise to let caller handle critical failure
            raise
    
    def add_to_maybe_sheet(self, sheet_id: str, opportunity: Dict, assessment: Dict):
        """Add opportunity to maybe sheet for review (scores 4-6)"""
        from sanitizer import Sanitizer
        
        # Sanitize data for sheets
        title = Sanitizer.sanitize_for_sheets(opportunity.get('title', ''))
        agency = Sanitizer.sanitize_for_sheets(opportunity.get('fullParentPathName', ''))
        
        # Get score label for display
        score = assessment.get('relevance_score', 0)
        score_display = self._get_score_label(score) if score >= 7 else str(score)
        
        row_data = [[
            score_display,  # Score with label
            title[:200],  # Title
            agency[:100],  # Agency
            opportunity.get('type', ''),  # Type
            opportunity.get('naicsCode', ''),  # NAICS
            opportunity.get('postedDate', ''),  # Posted
            opportunity.get('responseDeadLine', ''),  # Deadline
            ', '.join(assessment.get('uncertainty_factors', ['Unclear fit']))[:300],  # Uncertainty factors
            Sanitizer.sanitize_for_sheets(assessment.get('justification', ''))[:500],  # Justification
            Sanitizer.sanitize_for_sheets(assessment.get('ai_application', 'Potential application unclear'))[:300],  # AI Application
            f'=HYPERLINK("{opportunity.get("uiLink", "")}", "{opportunity.get("uiLink", "")}")',  # SAM Link
            opportunity.get('noticeId', ''),  # Notice ID
            datetime.now().strftime('%Y-%m-%d %H:%M')  # Evaluated
        ]]
        
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='A:M',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': row_data}
            ).execute()
            
            logger.info(f"Added to maybe sheet: {title[:50]}... (Score: {assessment.get('relevance_score', 0)})")
            
        except Exception as e:
            logger.error(f"Failed to add to maybe sheet: {str(e)}")
    
    def setup_spam_sheet_headers(self, sheet_id: str):
        """Setup headers for the spam sheet if needed"""
        try:
            # Check if headers exist
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:N1'
            ).execute()
            
            if not result.get('values'):
                # Add headers matching enhanced_discovery.py schema
                headers = [[
                    'AI Score',  # First column for easy sorting
                    'Status',    # Status emoji column
                    'Title',
                    'Agency',
                    'Type',
                    'NAICS',
                    'Posted',
                    'Deadline',
                    'AI Justification',
                    'AI Application',
                    'Similar Past RFPs',
                    'SAM Link',
                    'Notice ID',
                    'Evaluated'
                ]]
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range='A1:N1',
                    valueInputOption='USER_ENTERED',
                    body={'values': headers}
                ).execute()
                
                # Format header row
                requests = [{
                    'repeatCell': {
                        'range': {
                            'sheetId': 0,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {'bold': True, 'fontSize': 11},
                                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat'
                    }
                }]
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={'requests': requests}
                ).execute()
                
                logger.info("Set up spam sheet headers")
                
        except Exception as e:
            logger.warning(f"Could not setup spam sheet headers: {str(e)}")
    
    def update_opportunity_status(self, sheet_id: str, notice_id: str, status: str):
        """Update the status of an opportunity"""
        try:
            # Find the row with this notice ID
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Sheet1!E:E'  # Notice ID column
            ).execute()
            
            values = result.get('values', [])
            row_index = None
            
            for i, row in enumerate(values):
                if row and row[0] == notice_id:
                    row_index = i + 1  # 1-based index
                    break
            
            if row_index:
                # Update status column (C)
                self.service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=f'Sheet1!C{row_index}',
                    valueInputOption='USER_ENTERED',
                    body={'values': [[status]]}
                ).execute()
                
                logger.info(f"Updated status for {notice_id} to {status}")
            
        except Exception as e:
            logger.error(f"Error updating opportunity status: {str(e)}")
    
    def _format_sheet(self, sheet_id: str, worksheet_id: int):
        """Apply formatting to the sheet"""
        requests = [
            # Format header row
            {
                'repeatCell': {
                    'range': {
                        'sheetId': worksheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True, 'fontSize': 11},
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.4,
                                'blue': 0.8
                            },
                            'horizontalAlignment': 'CENTER',
                            'textColor': {'red': 1, 'green': 1, 'blue': 1}
                        }
                    },
                    'fields': 'userEnteredFormat'
                }
            },
            # Auto-resize columns
            {
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': worksheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 19
                    }
                }
            },
            # Add alternating row colors
            {
                'addBanding': {
                    'bandedRange': {
                        'bandedRangeId': 1,
                        'range': {
                            'sheetId': worksheet_id,
                            'startRowIndex': 1,
                            'endRowIndex': 1000
                        },
                        'rowProperties': {
                            'firstBandColor': {
                                'red': 1,
                                'green': 1,
                                'blue': 1
                            },
                            'secondBandColor': {
                                'red': 0.95,
                                'green': 0.95,
                                'blue': 0.95
                            }
                        }
                    }
                }
            }
        ]
        
        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to apply formatting: {str(e)}")
    
    def _add_checkbox(self, sheet_id: str, row: int, column: int):
        """Add checkbox data validation to a specific cell"""
        requests = [{
            'setDataValidation': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': row - 1,
                    'endRowIndex': row,
                    'startColumnIndex': column - 1,
                    'endColumnIndex': column
                },
                'rule': {
                    'condition': {
                        'type': 'BOOLEAN'
                    }
                }
            }
        }]
        
        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to add checkbox: {str(e)}")
    
    def _add_status_dropdown(self, sheet_id: str, row: int, column: int):
        """Add status dropdown validation to a specific cell"""
        status_values = [
            'New', 'Active', 'Expiring', 'Expired', 'Completed',
            'Submitted', 'In Progress', 'Won', 'Lost', 'Cancelled'
        ]
        
        requests = [{
            'setDataValidation': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': row - 1,
                    'endRowIndex': row,
                    'startColumnIndex': column - 1,
                    'endColumnIndex': column
                },
                'rule': {
                    'condition': {
                        'type': 'ONE_OF_LIST',
                        'values': [{'userEnteredValue': status} for status in status_values]
                    },
                    'showCustomUi': True,
                    'strict': False  # Allow custom values for backward compatibility
                }
            }
        }]
        
        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to add status dropdown: {str(e)}")
    
    def _apply_status_colors(self, sheet_id: str, row: int, status: str):
        """Apply color formatting to columns A-C based on status"""
        # Define colors
        colors = {
            'Expired': {'red': 1, 'green': 0.8, 'blue': 0.8},  # Light red
            'Completed': {'red': 0.8, 'green': 1, 'blue': 0.8},  # Light green
            'default': {'red': 1, 'green': 1, 'blue': 1}  # White
        }
        
        # Select color based on status
        if status == 'Expired':
            bg_color = colors['Expired']
        elif status == 'Completed':
            bg_color = colors['Completed']
        else:
            bg_color = colors['default']
        
        # Apply only if not default white
        if bg_color != colors['default']:
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row - 1,
                        'endRowIndex': row,
                        'startColumnIndex': 0,  # Column A
                        'endColumnIndex': 3      # Through column C
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': bg_color
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor'
                }
            }]
            
            try:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={'requests': requests}
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to apply status colors: {str(e)}")
    
    def _apply_imported_color(self, sheet_id: str, row: int):
        """Apply grey color formatting to imported RFPs in AI Score column"""
        requests = [{
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': row - 1,
                    'endRowIndex': row,
                    'startColumnIndex': 13,  # Column N (AI Score)
                    'endColumnIndex': 14
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.88, 'green': 0.88, 'blue': 0.88}  # Light grey
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        }]
        
        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to apply imported color: {str(e)}")
    
    def _apply_score_color(self, sheet_id: str, row: int, score: int):
        """Apply color formatting to AI Score column (N) based on score"""
        # Define score colors
        score_colors = {
            7: {'red': 1, 'green': 1, 'blue': 0},      # Yellow
            8: {'red': 0, 'green': 1, 'blue': 0},      # Green
            9: {'red': 0, 'green': 1, 'blue': 1},      # Cyan
            10: {'red': 1, 'green': 0.75, 'blue': 0.8} # Pink
        }
        
        if score in score_colors:
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row - 1,
                        'endRowIndex': row,
                        'startColumnIndex': 13,  # Column N (AI Score)
                        'endColumnIndex': 14
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': score_colors[score]
                        }
                    },
                    'fields': 'userEnteredFormat.backgroundColor'
                }
            }]
            
            try:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={'requests': requests}
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to apply score color: {str(e)}")
    
    def _share_sheet(self, sheet_id: str):
        """Share the sheet with appropriate permissions"""
        try:
            # You can modify this to share with specific emails
            # For now, we'll just log the URL
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            logger.info(f"Sheet created and available at: {sheet_url}")
        except Exception as e:
            logger.warning(f"Failed to share sheet: {str(e)}")