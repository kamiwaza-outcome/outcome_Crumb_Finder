#!/usr/bin/env python3
"""
Regenerate info docs for a few RFPs to show proof of concept with full data extraction
"""

import os
import sys
from datetime import datetime, timedelta
import logging
from typing import Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sheets_manager import SheetsManager
from src.drive_manager import DriveManager
from src.sam_client import SAMClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_folder_id(folder_link: str) -> str:
    """Extract folder ID from a Google Drive link"""
    if 'HYPERLINK' in folder_link:
        import re
        match = re.search(r'"(https://[^"]+)"', folder_link)
        if match:
            folder_link = match.group(1)
    
    if '/folders/' in folder_link:
        folder_id = folder_link.split('/folders/')[-1].split('?')[0]
        return folder_id
    
    return None

def main():
    logger.info("="*80)
    logger.info("PROOF OF CONCEPT: REGENERATING INFO DOCS WITH FULL DATA EXTRACTION")
    logger.info("="*80)
    
    # Initialize services
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    sam_client = SAMClient(Config.SAM_API_KEY)
    
    # Get a few specific RFPs to demonstrate
    logger.info("\n📋 Selecting sample RFPs for proof of concept...")
    
    # Get sheet data
    formula_result = sheets_manager.service.spreadsheets().values().get(
        spreadsheetId=Config.SPREADSHEET_ID,
        range='Sheet1!A:T',
        valueRenderOption='FORMULA'
    ).execute()
    
    values = formula_result.get('values', [])
    if len(values) < 2:
        logger.error("No data in sheet")
        return
    
    headers = values[0]
    col_indices = {header: i for i, header in enumerate(headers)}
    
    # Select 3 RFPs for proof of concept (rows with info docs that need updating)
    demo_rows = [226, 228, 230]  # RFI for DaaS, ONR Industry Day, AI Call for Solutions
    demo_rfps = []
    
    for row_num in demo_rows:
        if row_num <= len(values):
            row = values[row_num - 1]
            rfp = {
                'row_number': row_num,
                'notice_id': row[col_indices.get('Notice ID', 4)] if len(row) > 4 else '',
                'title': row[col_indices.get('Title', 6)] if len(row) > 6 else '',
                'folder_link': row[col_indices.get('Drive Folder', 12)] if len(row) > 12 else '',
            }
            if rfp['notice_id'] and rfp['folder_link']:
                demo_rfps.append(rfp)
                logger.info(f"  • {rfp['title'][:60]}")
    
    if not demo_rfps:
        logger.error("Could not find demo RFPs")
        return
    
    # Fetch ALL RFPs from SAM.gov for the date range
    logger.info(f"\n🔍 Fetching RFPs from SAM.gov database...")
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y')
    today = datetime.now().strftime('%m/%d/%Y')
    
    all_rfps = {}
    offset = 0
    limit = 1000
    
    while True:
        try:
            params = {
                'api_key': sam_client.api_key,
                'postedFrom': week_ago,
                'postedTo': today,
                'limit': limit,
                'offset': offset,
                'ptype': 'o,p,r,g,s'
            }
            
            response = sam_client._make_request(params)
            if not response:
                break
                
            opportunities = response.get('opportunitiesData', [])
            total_records = response.get('totalRecords', 0)
            
            for opp in opportunities:
                notice_id = opp.get('noticeId')
                if notice_id:
                    all_rfps[notice_id] = opp
            
            logger.info(f"  Fetched {len(opportunities)} RFPs (total: {len(all_rfps)}/{total_records})")
            
            if offset + limit >= total_records:
                break
            offset += limit
            
        except Exception as e:
            logger.error(f"Error fetching RFPs: {str(e)}")
            break
    
    logger.info(f"✅ Loaded {len(all_rfps)} RFPs from SAM.gov")
    
    # Process each demo RFP
    logger.info("\n" + "="*80)
    logger.info("CREATING ENHANCED INFO DOCUMENTS")
    logger.info("="*80)
    
    for i, rfp in enumerate(demo_rfps, 1):
        logger.info(f"\n[{i}/3] Processing: {rfp['title'][:60]}...")
        
        # Extract folder ID
        folder_id = extract_folder_id(rfp['folder_link'])
        if not folder_id:
            logger.error("   ❌ Could not extract folder ID")
            continue
        
        logger.info(f"   📁 Folder ID: {folder_id}")
        
        # Look up the RFP data
        opportunity = all_rfps.get(rfp['notice_id'])
        if not opportunity:
            logger.warning(f"   ⚠️  RFP not found in SAM.gov data")
            continue
        
        # Show what data we have
        logger.info("   📊 Available data fields:")
        logger.info(f"      • Title: {opportunity.get('title', 'N/A')[:50]}")
        logger.info(f"      • Agency: {opportunity.get('fullParentPathName', 'N/A')[:50]}")
        logger.info(f"      • Type: {opportunity.get('type', 'N/A')}")
        logger.info(f"      • Response Deadline: {opportunity.get('responseDeadLine', 'N/A')}")
        logger.info(f"      • Description URL: {'Yes' if opportunity.get('description', '').startswith('http') else 'No'}")
        logger.info(f"      • Contacts: {len(opportunity.get('pointOfContact', []))}")
        resource_links = opportunity.get('resourceLinks')
        if resource_links is None:
            resource_links = []
        logger.info(f"      • Resource Links: {len(resource_links) if isinstance(resource_links, list) else 0}")
        
        # Create the enhanced info document
        logger.info("   📝 Creating comprehensive info document with full data...")
        try:
            info_doc_link = drive_manager.create_info_document(opportunity, folder_id)
            
            if info_doc_link:
                logger.info(f"   ✅ SUCCESS! Created enhanced info doc")
                logger.info(f"   📄 Document link: {info_doc_link}")
                
                # Update the sheet
                range_name = f'Sheet1!S{rfp["row_number"]}'
                sheets_manager.service.spreadsheets().values().update(
                    spreadsheetId=Config.SPREADSHEET_ID,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body={'values': [[f'=HYPERLINK("{info_doc_link}", "Full Info v2")']]}
                ).execute()
                logger.info(f"   ✅ Updated spreadsheet with new link")
                
            else:
                logger.error("   ❌ Failed to create info document")
                
        except Exception as e:
            logger.error(f"   ❌ Error creating document: {str(e)}")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("PROOF OF CONCEPT COMPLETE")
    logger.info("="*80)
    logger.info("The enhanced info documents now contain:")
    logger.info("  ✓ Full description text (not just links)")
    logger.info("  ✓ Complete agency hierarchy")
    logger.info("  ✓ All contact information")
    logger.info("  ✓ Office addresses")
    logger.info("  ✓ Place of performance details")
    logger.info("  ✓ Classification codes with descriptions")
    logger.info("  ✓ Resource links and attachments")
    logger.info("\n🎉 Check the Google Docs to see the full extracted content!")

if __name__ == "__main__":
    main()