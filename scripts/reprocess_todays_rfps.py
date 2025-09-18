#!/usr/bin/env python3
"""
Reprocess today's RFPs to add comprehensive info documents
"""

import os
import sys
from datetime import datetime, timedelta
import logging
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sheets_manager import SheetsManager
from src.drive_manager import DriveManager
from src.sam_client import SAMClient
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_todays_rfps(sheets_manager: SheetsManager, include_cleared: bool = False) -> List[Dict]:
    """Get all RFPs added today from the main sheet, or specific cleared RFPs"""
    try:
        # Get formulas for Drive Folder column
        formula_result = sheets_manager.service.spreadsheets().values().get(
            spreadsheetId=Config.SPREADSHEET_ID,
            range='Sheet1!A:T',
            valueRenderOption='FORMULA'
        ).execute()
        
        # Get formatted values for dates
        formatted_result = sheets_manager.service.spreadsheets().values().get(
            spreadsheetId=Config.SPREADSHEET_ID,
            range='Sheet1!S:T',
            valueRenderOption='FORMATTED_VALUE'
        ).execute()
        
        values = formula_result.get('values', [])
        date_values = formatted_result.get('values', [])
        if len(values) < 2:
            return []
        
        headers = values[0]
        
        # Find column indices
        col_indices = {}
        for i, header in enumerate(headers):
            col_indices[header] = i
            
        # Log the headers and their indices for debugging
        logger.info(f"Sheet headers: {headers}")
        logger.info(f"Column indices: {col_indices}")
        
        today = datetime.now().strftime('%Y-%m-%d')
        todays_rfps = []
        
        # Rows that had info docs cleared (15 RFPs from earlier)
        cleared_rows = [226, 228, 229, 230, 231, 232, 237, 238, 241, 242, 244, 245, 246, 247, 248] if include_cleared else []
        
        for row_num, row in enumerate(values[1:], start=2):
            # Get the formatted date from the date_values array
            # Column S is index 0, Column T is index 1 in date_values
            date_added = None
            if row_num <= len(date_values):
                date_row = date_values[row_num - 1]  # -1 because date_values is 0-indexed
                if len(date_row) > 0:
                    date_added = date_row[0]  # Column S (first column in our S:T range)
            
            # Check if this RFP was added today OR is in the cleared list
            if (date_added and today in str(date_added)) or (row_num in cleared_rows):
                # Check if it has an info doc - the column might not exist yet
                # If there's an "Info Doc" header, use it; otherwise no RFPs have info docs
                info_doc_col = col_indices.get('Info Doc', None)
                
                if info_doc_col is not None:
                    # Column exists, check if this row has a value
                    has_info_doc = len(row) > info_doc_col and row[info_doc_col] and 'HYPERLINK' in str(row[info_doc_col])
                else:
                    # Column doesn't exist, so no RFPs have info docs
                    has_info_doc = False
                
                rfp = {
                    'row_number': row_num,
                    'notice_id': row[col_indices.get('Notice ID', 4)] if len(row) > 4 else '',
                    'title': row[col_indices.get('Title', 6)] if len(row) > 6 else '',
                    'folder_link': row[col_indices.get('Drive Folder', 12)] if len(row) > 12 else '',
                    'has_info_doc': has_info_doc,
                    'row_data': row
                }
                
                if rfp['notice_id'] and rfp['folder_link']:
                    todays_rfps.append(rfp)
                    logger.info(f"Found RFP: {rfp['title'][:50]} - Has info doc: {has_info_doc}")
        
        return todays_rfps
        
    except Exception as e:
        logger.error(f"Error getting today's RFPs: {str(e)}")
        return []

def extract_folder_id(folder_link: str) -> str:
    """Extract folder ID from a Google Drive link"""
    # Handle HYPERLINK formula
    if 'HYPERLINK' in folder_link:
        # Extract URL from HYPERLINK formula
        import re
        match = re.search(r'"(https://[^"]+)"', folder_link)
        if match:
            folder_link = match.group(1)
    
    # Extract folder ID from URL
    if '/folders/' in folder_link:
        folder_id = folder_link.split('/folders/')[-1].split('?')[0]
        return folder_id
    
    return None

def fetch_all_rfps_from_sam(sam_client: SAMClient, date_from: str, date_to: str) -> Dict[str, Dict]:
    """Fetch ALL RFPs from SAM.gov for a date range and return as dict keyed by noticeId"""
    logger.info(f"Fetching all RFPs from SAM.gov between {date_from} and {date_to}...")
    
    all_rfps = {}
    offset = 0
    limit = 1000
    total_fetched = 0
    
    while True:
        try:
            params = {
                'api_key': sam_client.api_key,
                'postedFrom': date_from,
                'postedTo': date_to,
                'limit': limit,
                'offset': offset,
                'ptype': 'o,p,r,g,s'  # All opportunity types
            }
            
            response = sam_client._make_request(params)
            if not response:
                break
                
            opportunities = response.get('opportunitiesData', [])
            total_records = response.get('totalRecords', 0)
            
            # Add each opportunity to our dict, keyed by noticeId
            for opp in opportunities:
                notice_id = opp.get('noticeId')
                if notice_id:
                    all_rfps[notice_id] = opp
                    total_fetched += 1
            
            logger.info(f"Fetched {len(opportunities)} RFPs (total: {total_fetched}/{total_records})")
            
            # Check if we've fetched all records
            if offset + limit >= total_records:
                break
            
            offset += limit
            
        except Exception as e:
            logger.error(f"Error fetching RFPs batch at offset {offset}: {str(e)}")
            break
    
    logger.info(f"Total RFPs fetched from SAM.gov: {len(all_rfps)}")
    return all_rfps

def main():
    logger.info("="*60)
    logger.info("REPROCESSING TODAY'S RFPs WITH COMPREHENSIVE INFO DOCS")
    logger.info("="*60)
    
    # Initialize services
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    sam_client = SAMClient(Config.SAM_API_KEY)
    
    # Get today's RFPs from the sheet (including the 15 cleared ones)
    logger.info("\n📋 Getting today's RFPs from main sheet (including cleared ones)...")
    todays_rfps = get_todays_rfps(sheets_manager, include_cleared=True)
    
    if not todays_rfps:
        logger.info("No RFPs found from today")
        return
    
    logger.info(f"Found {len(todays_rfps)} RFPs from today")
    
    # Fetch ALL RFPs from SAM.gov for a wider date range to catch misdated entries
    today = datetime.now().strftime('%m/%d/%Y')
    # Use a 7-day window to catch RFPs that might have different posted dates
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y')
    
    logger.info(f"\n🔍 Fetching all RFPs from SAM.gov for date range {week_ago} to {today}...")
    sam_rfps = fetch_all_rfps_from_sam(sam_client, week_ago, today)
    
    if not sam_rfps:
        logger.error("Failed to fetch RFPs from SAM.gov")
        return
    
    logger.info(f"Fetched {len(sam_rfps)} RFPs from SAM.gov")
    
    # Process each RFP
    processed = 0
    skipped = 0
    failed = 0
    not_found = 0
    
    for rfp in todays_rfps:
        try:
            # Skip if already has info doc
            if rfp['has_info_doc']:
                logger.info(f"⏭️  Skipping {rfp['title'][:40]} - already has info doc")
                skipped += 1
                continue
            
            logger.info(f"\n📄 Processing: {rfp['title'][:50]}...")
            
            # Extract folder ID
            folder_id = extract_folder_id(rfp['folder_link'])
            if not folder_id:
                logger.error(f"   ❌ Could not extract folder ID from link")
                failed += 1
                continue
            
            logger.info(f"   📁 Folder ID: {folder_id}")
            
            # Look up the RFP in our fetched data by notice ID
            opportunity = sam_rfps.get(rfp['notice_id'])
            
            if not opportunity:
                logger.warning(f"   ⚠️  RFP not found in SAM.gov data (Notice ID: {rfp['notice_id']})")
                not_found += 1
                continue
            
            # Create comprehensive info document
            logger.info(f"   📝 Creating comprehensive info document...")
            info_doc_link = drive_manager.create_info_document(opportunity, folder_id)
            
            if info_doc_link:
                logger.info(f"   ✅ Created info doc successfully")
                
                # Update the sheet with the info doc link
                try:
                    # Info Doc column is column S (index 18)
                    range_name = f'Sheet1!S{rfp["row_number"]}'
                    
                    sheets_manager.service.spreadsheets().values().update(
                        spreadsheetId=Config.SPREADSHEET_ID,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body={'values': [[f'=HYPERLINK("{info_doc_link}", "Full Info")']]}
                    ).execute()
                    
                    logger.info(f"   ✅ Updated sheet with info doc link")
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to update sheet: {str(e)}")
                    failed += 1
            else:
                logger.error(f"   ❌ Failed to create info document")
                failed += 1
                
        except Exception as e:
            logger.error(f"Error processing RFP {rfp['title'][:30]}: {str(e)}")
            failed += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("REPROCESSING COMPLETE")
    logger.info("="*60)
    logger.info(f"✅ Processed: {processed}")
    logger.info(f"⏭️  Skipped (already had docs): {skipped}")
    logger.info(f"⚠️  Not found in SAM.gov: {not_found}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Total: {len(todays_rfps)}")
    
    if not_found > 0:
        logger.warning(f"\n⚠️  {not_found} RFPs were not found in SAM.gov data - they may have been posted on a different date")
    if failed > 0:
        logger.warning(f"\n⚠️  {failed} RFPs failed to process - check logs for details")
    
    if not_found == 0 and failed == 0:
        logger.info("\n🎉 All RFPs processed successfully!")

if __name__ == "__main__":
    main()