#!/usr/bin/env python3
"""
Import RFP from SAM.gov URL
Handles manual imports via Slack command or direct script execution
"""

import os
import sys
import json
import logging
import argparse
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import sys
import os
# Add parent directory to path to import from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sam_client import SAMClient
from src.ai_qualifier import AIQualifier
from src.drive_manager import DriveManager
from src.sheets_manager import SheetsManager
from src.slack_notifier import SlackNotifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RFPImporter:
    """Handle importing RFPs from SAM.gov URLs"""
    
    def __init__(self):
        """Initialize all required services"""
        self.sam_client = SAMClient(Config.SAM_API_KEY)
        self.ai_qualifier = AIQualifier(Config.OPENAI_API_KEY)
        self.drive_manager = DriveManager(Config.GOOGLE_DRIVE_CREDS_PATH)
        self.sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
        if Config.SLACK_WEBHOOK_URL:
            self.slack_notifier = SlackNotifier(Config.SLACK_WEBHOOK_URL)
        else:
            self.slack_notifier = None
    
    def extract_notice_id(self, url: str) -> Optional[str]:
        """Extract notice ID from SAM.gov URL"""
        try:
            # Handle various SAM.gov URL formats
            # https://sam.gov/opp/{noticeId}/view
            # https://beta.sam.gov/opp/{noticeId}/view
            if 'sam.gov/opp/' in url:
                parts = url.split('/opp/')[1].split('/')
                if parts:
                    return parts[0]
            return None
        except Exception as e:
            logger.error(f"Error extracting notice ID from URL: {str(e)}")
            return None
    
    def check_existing_rfp(self, notice_id: str) -> Dict:
        """Check if RFP already exists in any sheet"""
        result = {
            'exists': False,
            'location': None,
            'sheet_name': None,
            'row': None,
            'ai_score': None,
            'status': None
        }
        
        sheets_to_check = [
            ('Main', Config.SPREADSHEET_ID),
            ('Maybe', Config.MAYBE_SPREADSHEET_ID),
            ('Spam', Config.SPAM_SPREADSHEET_ID)
        ]
        
        for sheet_name, sheet_id in sheets_to_check:
            if not sheet_id:
                continue
                
            try:
                # Get all notice IDs from the sheet
                range_name = 'A:N'  # Get all relevant columns
                response = self.sheets_manager.service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range=range_name
                ).execute()
                
                values = response.get('values', [])
                
                # Find the notice ID (column A)
                for idx, row in enumerate(values[1:], start=2):  # Skip header
                    if row and len(row) > 0 and row[0] == notice_id:
                        result['exists'] = True
                        result['location'] = sheet_id
                        result['sheet_name'] = sheet_name
                        result['row'] = idx
                        # Try to get AI score from column N (index 13)
                        if len(row) > 13:
                            result['ai_score'] = row[13]
                        # Get status from column C (index 2)
                        if len(row) > 2:
                            result['status'] = row[2]
                        return result
                        
            except Exception as e:
                logger.error(f"Error checking {sheet_name} sheet: {str(e)}")
                continue
        
        return result
    
    def import_rfp(self, url: str, user: str = None) -> Dict:
        """
        Import an RFP from a SAM.gov URL
        
        Args:
            url: SAM.gov opportunity URL
            user: Username/ID of person requesting import (from Slack)
            
        Returns:
            Dict with import results and status
        """
        result = {
            'success': False,
            'message': '',
            'notice_id': None,
            'row': None,
            'details': {}
        }
        
        # Step 1: Extract notice ID
        notice_id = self.extract_notice_id(url)
        if not notice_id:
            result['message'] = "❌ Invalid SAM.gov URL format. Expected: https://sam.gov/opp/{noticeId}/view"
            return result
        
        result['notice_id'] = notice_id
        logger.info(f"Importing RFP with notice ID: {notice_id}")
        
        # Step 2: Check for existing RFP
        existing = self.check_existing_rfp(notice_id)
        
        if existing['exists'] and existing['sheet_name'] == 'Main':
            result['message'] = (
                f"❌ Already tracking in Main Sheet (Row {existing['row']})\n"
                f"Current Status: {existing['status'] or 'Unknown'}"
            )
            return result
        
        # Step 3: Fetch from SAM API
        try:
            opportunity = self.sam_client.get_opportunity_details(notice_id)
            if not opportunity:
                result['message'] = "❌ Could not find RFP. It may be expired, removed, or the notice ID is invalid."
                return result
        except Exception as e:
            logger.error(f"Error fetching from SAM API: {str(e)}")
            result['message'] = f"❌ Error fetching RFP data: {str(e)}"
            return result
        
        # Step 4: Run AI assessment
        try:
            assessment = self.ai_qualifier.evaluate_opportunity(opportunity)
            if not assessment:
                assessment = {
                    'relevance_score': 0,
                    'justification': 'Manual import - AI assessment failed',
                    'ai_application': 'To be determined',
                    'key_requirements': [],
                    'suggested_approach': 'Manual review required'
                }
        except Exception as e:
            logger.error(f"AI assessment failed: {str(e)}")
            assessment = {
                'relevance_score': 0,
                'justification': 'Manual import - AI assessment unavailable',
                'ai_application': 'To be determined',
                'key_requirements': [],
                'suggested_approach': 'Manual review required'
            }
        
        # Step 5: Create Drive folder
        try:
            folder_url = self.drive_manager.create_opportunity_folder(
                opportunity, 
                assessment,
                parent_folder_id=Config.DAILY_RFPS_FOLDER_ID
            )
        except Exception as e:
            logger.error(f"Error creating Drive folder: {str(e)}")
            folder_url = "Error creating folder"
        
        # Step 6: Add to Main Sheet with "Imported" marker
        try:
            # Store the original AI score but display "Imported"
            import_assessment = assessment.copy()
            import_assessment['original_score'] = assessment.get('relevance_score', 0)
            import_assessment['is_imported'] = True
            import_assessment['imported_by'] = user or 'Unknown'
            import_assessment['import_date'] = datetime.now().isoformat()
            
            # If it existed in Maybe/Spam, note that
            if existing['exists']:
                import_assessment['previous_location'] = existing['sheet_name']
                import_assessment['previous_row'] = existing['row']
                import_assessment['previous_score'] = existing['ai_score']
            
            # Add to main sheet
            self.sheets_manager.add_opportunity(
                Config.SPREADSHEET_ID,
                opportunity,
                import_assessment,
                folder_url
            )
            
            # Get the row number we just added
            check_result = self.check_existing_rfp(notice_id)
            result['row'] = check_result.get('row')
            
        except Exception as e:
            logger.error(f"Error adding to sheet: {str(e)}")
            result['message'] = f"❌ Error adding to sheet: {str(e)}"
            return result
        
        # Step 7: Download attachments to Drive folder
        if opportunity.get('attachments'):
            try:
                # Extract folder ID from URL
                folder_id = folder_url.split('/folders/')[1] if '/folders/' in folder_url else None
                if folder_id:
                    for attachment in opportunity['attachments'][:10]:  # Limit to 10 attachments
                        try:
                            self.sam_client.download_attachment(
                                attachment,
                                folder_id,
                                self.drive_manager
                            )
                        except Exception as e:
                            logger.warning(f"Failed to download attachment: {e}")
            except Exception as e:
                logger.warning(f"Error downloading attachments: {str(e)}")
        
        # Step 8: Build success message
        result['success'] = True
        result['details'] = {
            'title': opportunity.get('title', 'Unknown'),
            'agency': opportunity.get('fullParentPathName', 'Unknown'),
            'deadline': opportunity.get('responseDeadLine', 'Not specified'),
            'posted': opportunity.get('postedDate', 'Unknown'),
            'folder_url': folder_url,
            'sam_url': opportunity.get('uiLink', url),
            'ai_score': assessment.get('relevance_score', 0),
            'was_duplicate': existing['exists']
        }
        
        # Build detailed message
        message_parts = [
            "=" * 43,
            "✅ IMPORTED TO MAIN SHEET",
            "=" * 43,
            f"Row: {result['row']} | Status: {self._calculate_status(opportunity)}",
            "",
            "📋 RFP DETAILS",
            f"Title: {opportunity.get('title', 'Unknown')[:80]}",
            f"Agency: {opportunity.get('fullParentPathName', 'Unknown')}",
            f"Deadline: {opportunity.get('responseDeadLine', 'Not specified')}",
            f"Posted: {opportunity.get('postedDate', 'Unknown')}",
            "",
            "🤖 AI ASSESSMENT"
        ]
        
        if existing['exists']:
            message_parts.append(f"Score: Imported (Originally {existing['ai_score']})")
            message_parts.append(f"Previous Location: {existing['sheet_name']} Sheet Row {existing['row']}")
            message_parts.append("")
            message_parts.append("⚠️ FEEDBACK NEEDED?")
            message_parts.append(f"This RFP was previously filtered to {existing['sheet_name']} Sheet.")
            message_parts.append(f"If you believe the AI rating is incorrect,")
            message_parts.append("please contact Finn to improve the AI scraper.")
        else:
            message_parts.append(f"Score: Imported (AI rated {assessment.get('relevance_score', 0)}/10)")
            message_parts.append("")
            message_parts.append("📝 Note: If the AI rating seems incorrect,")
            message_parts.append("please contact Finn to improve the AI scraper.")
        
        message_parts.extend([
            "",
            "📁 RESOURCES",
            f"SAM.gov: {opportunity.get('uiLink', url)}",
            f"Drive Folder: {folder_url}",
            f"Sheet Row: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}/edit#gid=0&range=A{result['row']}",
            "",
            "💡 Tips:",
            "- Add notes in Column O for proposal ideas",
            "- Update Status column when pursuing",
            "- Check Drive folder for all attachments",
            "=" * 43
        ])
        
        result['message'] = "\n".join(message_parts)
        
        return result
    
    def _calculate_status(self, opportunity: Dict) -> str:
        """Calculate status based on dates"""
        try:
            from datetime import datetime
            
            today = datetime.now().date()
            
            # Parse deadline
            deadline_str = opportunity.get('responseDeadLine')
            if deadline_str:
                if 'T' in deadline_str:
                    deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date()
                else:
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                
                days_until = (deadline - today).days
                
                if days_until < 0:
                    return "Expired"
                elif days_until < 3:
                    return "Expiring"
                else:
                    return "Active"
            
            return "Active"
            
        except:
            return "Active"
    
    def send_slack_response(self, response_url: str, message: str):
        """Send response back to Slack"""
        try:
            response = requests.post(response_url, json={
                'text': message,
                'response_type': 'in_channel'  # Make visible to all
            })
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Slack response: {str(e)}")


def main():
    """Main entry point for command-line usage"""
    parser = argparse.ArgumentParser(description='Import RFP from SAM.gov URL')
    parser.add_argument('url', help='SAM.gov opportunity URL')
    parser.add_argument('--user', help='Username of person importing', default='CLI')
    parser.add_argument('--slack-response-url', help='Slack response URL for webhook responses')
    
    args = parser.parse_args()
    
    # Initialize importer
    importer = RFPImporter()
    
    # Import the RFP
    result = importer.import_rfp(args.url, args.user)
    
    # Print or send response
    if args.slack_response_url:
        importer.send_slack_response(args.slack_response_url, result['message'])
    else:
        print(result['message'])
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()