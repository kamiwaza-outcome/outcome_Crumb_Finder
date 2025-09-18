#!/usr/bin/env python3
"""
Add dropdown validation to Status column in Google Sheets
This ensures consistent status values across human and program edits
"""

import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_status_dropdowns(sheet_id: str):
    """Add dropdown validation to the Status column (C) with all possible statuses"""
    
    try:
        # Initialize Google Sheets service
        credentials = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_SHEETS_CREDS_PATH,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        # Define all possible status values
        status_values = [
            'New',
            'Active', 
            'Expiring',
            'Expired',
            'Completed',
            'Submitted',
            'In Progress',
            'Won',
            'Lost',
            'Cancelled'
        ]
        
        # Get sheet metadata to find the sheet ID
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheet_properties = sheet_metadata['sheets'][0]['properties']
        internal_sheet_id = sheet_properties['sheetId']
        row_count = sheet_properties['gridProperties']['rowCount']
        
        logger.info(f"Adding status dropdowns to sheet {sheet_id}")
        logger.info(f"Sheet has {row_count} rows")
        
        # Create the data validation rule
        requests = [
            {
                'setDataValidation': {
                    'range': {
                        'sheetId': internal_sheet_id,
                        'startRowIndex': 1,  # Start from row 2 (skip header)
                        'endRowIndex': row_count,  # Apply to all rows
                        'startColumnIndex': 2,  # Column C (0-indexed)
                        'endColumnIndex': 3     # Just column C
                    },
                    'rule': {
                        'condition': {
                            'type': 'ONE_OF_LIST',
                            'values': [{'userEnteredValue': status} for status in status_values]
                        },
                        'showCustomUi': True,  # Show dropdown arrow
                        'strict': False  # Allow other values (for backward compatibility)
                    }
                }
            }
        ]
        
        # Apply the validation rule
        body = {'requests': requests}
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body=body
        ).execute()
        
        logger.info(f"✅ Successfully added dropdown validation to Status column")
        logger.info(f"   Available options: {', '.join(status_values)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding status dropdowns: {str(e)}")
        return False

def update_all_sheets():
    """Add dropdowns to all configured sheets"""
    
    logger.info("="*60)
    logger.info("📝 ADDING STATUS DROPDOWNS TO ALL SHEETS")
    logger.info("="*60)
    
    sheets_updated = 0
    
    # Update main sheet
    if Config.SPREADSHEET_ID:
        logger.info("\n📋 Updating Main RFP Sheet...")
        if add_status_dropdowns(Config.SPREADSHEET_ID):
            sheets_updated += 1
    
    # Update maybe sheet
    if Config.MAYBE_SPREADSHEET_ID:
        logger.info("\n📋 Updating Maybe Sheet...")
        if add_status_dropdowns(Config.MAYBE_SPREADSHEET_ID):
            sheets_updated += 1
    
    # Update graveyard sheet (if it has data)
    if Config.GRAVEYARD_SPREADSHEET_ID:
        logger.info("\n📋 Updating Graveyard Sheet...")
        if add_status_dropdowns(Config.GRAVEYARD_SPREADSHEET_ID):
            sheets_updated += 1
    
    # Update bank sheet (if it has data)
    if Config.BANK_SPREADSHEET_ID:
        logger.info("\n📋 Updating Bank Sheet...")
        if add_status_dropdowns(Config.BANK_SPREADSHEET_ID):
            sheets_updated += 1
    
    logger.info("\n" + "="*60)
    logger.info(f"✨ Complete! Updated {sheets_updated} sheets with status dropdowns")
    logger.info("="*60)
    
    return sheets_updated > 0

if __name__ == "__main__":
    import sys
    success = update_all_sheets()
    sys.exit(0 if success else 1)