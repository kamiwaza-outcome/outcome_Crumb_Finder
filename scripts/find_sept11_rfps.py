#!/usr/bin/env python3
"""Find all RFPs from Sept 11, 2025 in the main sheet"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sheets_manager import SheetsManager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_sept11_rfps():
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Get formatted values to see dates
    result = sheets_manager.service.spreadsheets().values().get(
        spreadsheetId=Config.SPREADSHEET_ID,
        range='Sheet1!A:T',
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    
    values = result.get('values', [])
    
    if not values:
        logger.info("No data found")
        return
    
    headers = values[0]
    logger.info(f"Headers: {headers}")
    
    # Find Date Added column (should be column T, index 19)
    date_col_index = None
    for i, header in enumerate(headers):
        if 'Date Added' in header:
            date_col_index = i
            break
    
    if date_col_index is None:
        logger.error("Could not find Date Added column")
        return
    
    logger.info(f"Date Added column is at index {date_col_index} (column {chr(65 + date_col_index)})")
    
    # Search for Sept 11 RFPs
    sept11_rfps = []
    for row_num in range(1, len(values)):
        row = values[row_num]
        if len(row) > date_col_index:
            date_value = row[date_col_index]
            if date_value and ('2025-09-11' in str(date_value) or '9/11/2025' in str(date_value) or 'Sep 11' in str(date_value) or 'September 11' in str(date_value)):
                title = row[6] if len(row) > 6 else 'Unknown'
                notice_id = row[4] if len(row) > 4 else 'Unknown'
                sept11_rfps.append({
                    'row': row_num + 1,  # 1-indexed for sheets
                    'title': title[:50],
                    'notice_id': notice_id,
                    'date': date_value
                })
    
    if sept11_rfps:
        logger.info(f"\n✅ Found {len(sept11_rfps)} RFPs from Sept 11, 2025:")
        logger.info(f"Row range: {sept11_rfps[0]['row']} to {sept11_rfps[-1]['row']}")
        for rfp in sept11_rfps[:5]:  # Show first 5
            logger.info(f"  Row {rfp['row']}: {rfp['title']}... ({rfp['date']})")
        if len(sept11_rfps) > 5:
            logger.info(f"  ... and {len(sept11_rfps) - 5} more")
    else:
        logger.info("\n❌ No RFPs found from Sept 11, 2025")
        
        # Show what dates we do have in recent rows
        logger.info("\nRecent dates found:")
        for row_num in range(max(1, len(values) - 50), len(values)):
            if row_num < len(values):
                row = values[row_num]
                if len(row) > date_col_index and row[date_col_index]:
                    logger.info(f"  Row {row_num + 1}: {row[date_col_index]}")

if __name__ == "__main__":
    find_sept11_rfps()