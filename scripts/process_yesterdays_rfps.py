#!/usr/bin/env python3
"""
Process yesterday's RFPs to add comprehensive info documents
"""

import os
import sys
from datetime import datetime, timedelta
import logging
import re
from typing import List, Dict, Optional
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sheets_manager import SheetsManager
from src.drive_manager import DriveManager
from src.sam_client import SAMClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_folder_id(folder_link: str) -> Optional[str]:
    """Extract folder ID from a Google Drive HYPERLINK formula"""
    if 'HYPERLINK' in folder_link:
        # Extract URL from HYPERLINK formula
        match = re.search(r'"(https://[^"]+)"', folder_link)
        if match:
            folder_link = match.group(1)
    
    # Extract folder ID from URL
    if '/folders/' in folder_link:
        folder_id = folder_link.split('/folders/')[-1].split('?')[0]
        return folder_id
    
    return None

def get_yesterdays_rfps(sheets_manager: SheetsManager) -> List[Dict]:
    """Get all RFPs from yesterday (Sept 11, 2025) from the main sheet"""
    try:
        # Get formulas for Drive Folder links
        formula_result = sheets_manager.service.spreadsheets().values().get(
            spreadsheetId=Config.SPREADSHEET_ID,
            range='Sheet1!A:T',
            valueRenderOption='FORMULA'
        ).execute()
        
        # Get formatted values for readable data
        formatted_result = sheets_manager.service.spreadsheets().values().get(
            spreadsheetId=Config.SPREADSHEET_ID,
            range='Sheet1!A:T',
            valueRenderOption='FORMATTED_VALUE'
        ).execute()
        
        formula_values = formula_result.get('values', [])
        formatted_values = formatted_result.get('values', [])
        
        if len(formula_values) < 2:
            return []
        
        headers = formula_values[0]
        
        # Find column indices
        col_indices = {}
        for i, header in enumerate(headers):
            col_indices[header] = i
        
        # Yesterday's date (Sept 11, 2025)
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        logger.info(f"Looking for RFPs from: {yesterday}")
        
        yesterdays_rfps = []
        
        # Search through all rows to find yesterday's RFPs
        for row_num in range(1, len(formula_values)):
            if row_num >= len(formatted_values):
                break
                
            formula_row = formula_values[row_num]
            formatted_row = formatted_values[row_num]
            
            # Get the date from formatted values - it's in column S (index 18)
            date_added = None
            if len(formatted_row) > 18:  # Column S
                date_added = formatted_row[18]
            
            # Check if this RFP was added yesterday (Sept 11)
            if date_added and ('2025-09-11' in str(date_added) or '9/11/2025' in str(date_added)):
                # Get notice ID and title
                notice_id = formatted_row[col_indices.get('Notice ID', 4)] if len(formatted_row) > 4 else ''
                title = formatted_row[col_indices.get('Title', 6)] if len(formatted_row) > 6 else ''
                
                # Get folder link from formula row
                folder_link = formula_row[col_indices.get('Drive Folder', 12)] if len(formula_row) > 12 else ''
                
                # Check if it already has an info doc (column T now, was S)
                has_info_doc = False
                if len(formula_row) > 19:  # Column T (index 19)
                    info_doc_cell = formula_row[19]
                    has_info_doc = info_doc_cell and 'HYPERLINK' in str(info_doc_cell)
                
                rfp = {
                    'row_number': row_num + 1,  # 1-indexed for sheets
                    'notice_id': notice_id,
                    'title': title,
                    'folder_link': folder_link,
                    'has_info_doc': has_info_doc,
                    'date_added': date_added
                }
                
                if notice_id and folder_link:
                    yesterdays_rfps.append(rfp)
                    logger.info(f"Found RFP from {date_added}: {title[:50]}... - Has info doc: {has_info_doc}")
        
        return yesterdays_rfps
        
    except Exception as e:
        logger.error(f"Error getting yesterday's RFPs: {str(e)}")
        return []

def fetch_rfp_from_sam(sam_client: SAMClient, date: str = None) -> Dict[str, Dict]:
    """Fetch all RFPs from a specific date"""
    if not date:
        date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
    
    logger.info(f"Fetching RFPs from SAM.gov for {date}...")
    
    all_opportunities = []
    offset = 0
    limit = 1000
    
    while True:
        params = {
            'api_key': sam_client.api_key,
            'postedFrom': date,
            'postedTo': date,
            'limit': limit,
            'offset': offset
        }
        
        response = sam_client._make_request(params)
        if not response:
            break
            
        opportunities = response.get('opportunitiesData', [])
        if not opportunities:
            break
            
        all_opportunities.extend(opportunities)
        
        # Check if there are more pages
        if len(opportunities) < limit:
            break
        
        offset += limit
        time.sleep(0.5)  # Be nice to the API
    
    # Create a dictionary keyed by notice ID
    opp_dict = {}
    for opp in all_opportunities:
        notice_id = opp.get('noticeId')
        if notice_id:
            opp_dict[notice_id] = opp
    
    logger.info(f"Fetched {len(opp_dict)} opportunities from SAM.gov")
    return opp_dict

def main():
    logger.info("="*60)
    logger.info("PROCESSING YESTERDAY'S RFPs WITH COMPREHENSIVE INFO DOCS")
    logger.info("="*60)
    
    # Initialize services
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    sam_client = SAMClient(Config.SAM_API_KEY)
    
    # Get yesterday's RFPs from the sheet
    logger.info("\n📋 Getting yesterday's RFPs from main sheet...")
    yesterdays_rfps = get_yesterdays_rfps(sheets_manager)
    
    if not yesterdays_rfps:
        logger.info("No RFPs found from yesterday")
        return
    
    logger.info(f"Found {len(yesterdays_rfps)} RFPs from yesterday")
    
    # Fetch all RFPs from SAM.gov for yesterday
    sam_opportunities = fetch_rfp_from_sam(sam_client, '09/11/2025')
    
    # Process each RFP
    processed = 0
    skipped = 0
    failed = 0
    
    for rfp in yesterdays_rfps:
        try:
            # Skip if already has info doc
            if rfp['has_info_doc']:
                logger.info(f"⏭️  Skipping {rfp['title'][:40]}... - already has info doc")
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
            
            # Get RFP details from our fetched data
            opportunity = sam_opportunities.get(rfp['notice_id'])
            
            if not opportunity:
                logger.warning(f"   ⚠️  RFP not found in SAM.gov data for notice ID: {rfp['notice_id']}")
                failed += 1
                continue
            
            # Create comprehensive info document
            logger.info(f"   📝 Creating comprehensive info document...")
            info_doc_link = drive_manager.create_info_document(opportunity, folder_id)
            
            if info_doc_link:
                logger.info(f"   ✅ Created info doc successfully")
                
                # Update the sheet with the info doc link
                try:
                    # Update column T (Info Doc - column 20, 0-indexed = 19)
                    range_name = f'Sheet1!T{rfp["row_number"]}'
                    
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
                    # Still count as processed since doc was created
                    processed += 1
            else:
                logger.error(f"   ❌ Failed to create info document")
                failed += 1
            
            # Small delay to avoid rate limits
            time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error processing RFP {rfp['title'][:30]}: {str(e)}")
            failed += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("PROCESSING COMPLETE")
    logger.info("="*60)
    logger.info(f"✅ Processed: {processed}")
    logger.info(f"⏭️  Skipped (already had docs): {skipped}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Total: {len(yesterdays_rfps)}")
    
    if failed > 0:
        logger.warning(f"\n⚠️  {failed} RFPs failed to process - check logs for details")
    else:
        logger.info("\n🎉 All RFPs processed successfully!")

if __name__ == "__main__":
    main()