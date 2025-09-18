#!/usr/bin/env python3
"""
Update existing sheet links to show actual URLs instead of "View on SAM.gov" or "Link"
"""

import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import Config
import re
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_sheet_links(sheet_id: str, sheet_name: str = "Sheet1"):
    """Update all hyperlinks in a sheet to show the actual URL"""
    
    try:
        # Initialize Google Sheets service
        credentials = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_SHEETS_CREDS_PATH,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        logger.info(f"Processing {sheet_name} in sheet {sheet_id}")
        
        # Get all data from the sheet with formulas
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f'{sheet_name}!A:Z',
            valueRenderOption='FORMULA'  # Get formulas, not display values
        ).execute()
        
        values = result.get('values', [])
        if not values:
            logger.info("No data found in sheet")
            return 0
        
        updates_made = 0
        batch_updates = []
        
        # Search for HYPERLINK formulas
        for row_idx, row in enumerate(values):
            for col_idx, cell in enumerate(row):
                if isinstance(cell, str) and cell.startswith('=HYPERLINK'):
                    # Extract URL from HYPERLINK formula
                    match = re.match(r'=HYPERLINK\("([^"]+)",\s*"[^"]*"\)', cell)
                    if match:
                        url = match.group(1)
                        # Check if it's a SAM.gov link and display text is not the URL
                        if 'sam' in url.lower():
                            # Check if the display text is not already the URL
                            if '"View on SAM.gov"' in cell or '"Link"' in cell or url not in cell:
                                # Update to show the actual URL
                                new_formula = f'=HYPERLINK("{url}", "{url}")'
                                col_letter = chr(65 + col_idx)  # Convert to column letter
                                cell_range = f'{col_letter}{row_idx + 1}'
                                
                                batch_updates.append({
                                    'range': cell_range,
                                    'values': [[new_formula]]
                                })
                                updates_made += 1
                                
                                if updates_made <= 3:  # Log first few for debugging
                                    logger.debug(f"Found link at {cell_range}: {cell[:50]}...")
        
        # Apply all updates in batch
        if batch_updates:
            logger.info(f"Updating {len(batch_updates)} links...")
            
            # Split into smaller batches to avoid API limits
            batch_size = 50
            for i in range(0, len(batch_updates), batch_size):
                batch = batch_updates[i:i+batch_size]
                
                body = {
                    'valueInputOption': 'USER_ENTERED',
                    'data': batch
                }
                
                service.spreadsheets().values().batchUpdate(
                    spreadsheetId=sheet_id,
                    body=body
                ).execute()
                
                logger.info(f"Updated batch {i//batch_size + 1} ({len(batch)} cells)")
                time.sleep(1)  # Rate limiting
        
        logger.info(f"✅ Updated {updates_made} links in {sheet_name}")
        return updates_made
        
    except Exception as e:
        logger.error(f"Error updating sheet: {str(e)}")
        return 0

def main():
    """Update links in all configured sheets"""
    
    logger.info("="*60)
    logger.info("🔗 UPDATING SHEET LINKS TO SHOW ACTUAL URLS")
    logger.info("="*60)
    
    total_updates = 0
    
    # Update main sheet
    if Config.SPREADSHEET_ID:
        logger.info("\n📋 Updating Main RFP Sheet...")
        updates = update_sheet_links(Config.SPREADSHEET_ID)
        total_updates += updates
    
    # Update maybe sheet
    if Config.MAYBE_SPREADSHEET_ID:
        logger.info("\n📋 Updating Maybe Sheet...")
        updates = update_sheet_links(Config.MAYBE_SPREADSHEET_ID)
        total_updates += updates
    
    # Update spam sheet (all RFPs)
    if Config.SPAM_SPREADSHEET_ID:
        logger.info("\n📋 Updating All RFPs Sheet...")
        updates = update_sheet_links(Config.SPAM_SPREADSHEET_ID)
        total_updates += updates
    
    logger.info("\n" + "="*60)
    logger.info(f"✨ Complete! Updated {total_updates} total links")
    logger.info("="*60)

if __name__ == "__main__":
    main()