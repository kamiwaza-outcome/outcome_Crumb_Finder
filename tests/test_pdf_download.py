#!/usr/bin/env python3
"""
Test PDF download functionality
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sam_client import SAMClient
from drive_manager import DriveManager

def test_pdf_downloads():
    """Test downloading PDFs for a qualified RFP"""
    
    print("\n" + "="*60)
    print("📎 TESTING PDF DOWNLOAD FUNCTIONALITY")
    print("="*60)
    
    # Initialize
    sam_client = SAMClient(Config.SAM_API_KEY)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Search for today's RFPs (just get one)
    print("\n🔍 Finding a test RFP...")
    
    target_date = datetime.now().strftime('%m/%d/%Y')
    
    # Get one IT services RFP
    params = {
        'ncode': '541512',  # Computer Systems Design
        'postedFrom': target_date,
        'postedTo': target_date,
        'limit': 1,
        'offset': 0,
        'ptype': 'o,p,r',
        'api_key': sam_client.api_key
    }
    
    try:
        data = sam_client._make_request(params)
        opportunities = data.get('opportunitiesData', [])
        
        if not opportunities:
            print("No RFPs found today. Trying broader search...")
            # Try without date filter
            del params['postedFrom']
            del params['postedTo']
            params['limit'] = 3
            data = sam_client._make_request(params)
            opportunities = data.get('opportunitiesData', [])
        
        if opportunities:
            opp = opportunities[0]
            print(f"\n✓ Found: {opp.get('title', 'Unknown')[:60]}")
            print(f"  Notice ID: {opp.get('noticeId')}")
            print(f"  Agency: {opp.get('fullParentPathName', '')[:50]}")
            
            # Check for attachments
            print("\n📄 Checking for attachments...")
            attachments = sam_client.get_opportunity_attachments(opp)
            
            if attachments:
                print(f"  Found {len(attachments)} attachments:")
                for att in attachments[:5]:
                    print(f"    • {att['name']}")
                
                # Create a test folder in Drive
                print("\n📁 Creating Drive folder...")
                folder_name = f"TEST - {opp.get('noticeId', 'test')[:15]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                folder_url = drive_manager.get_folder_url(folder_id)
                
                print(f"  Folder created: {folder_url}")
                
                # Download and store attachments
                print("\n⬇️ Downloading attachments...")
                stored = drive_manager.store_rfp_attachments(opp, folder_id, sam_client)
                
                if stored:
                    print(f"\n✅ Successfully stored {len(stored)} documents!")
                    print(f"   View them at: {folder_url}")
                else:
                    print("\n⚠️ No documents were stored")
            else:
                print("  No attachments found for this RFP")
                
                # Still create folder with assessment
                print("\n📁 Creating Drive folder with assessment only...")
                folder_name = f"TEST - {opp.get('noticeId', 'test')[:15]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                
                # Add a test document
                test_doc = f"""TEST RFP ASSESSMENT
                
Title: {opp.get('title')}
Agency: {opp.get('fullParentPathName')}
Posted: {opp.get('postedDate')}

Description:
{opp.get('description', 'N/A')[:1000]}

Note: No PDF attachments were available for this RFP.
"""
                
                drive_manager.upload_file(
                    test_doc.encode('utf-8'),
                    'assessment.txt',
                    folder_id,
                    'text/plain'
                )
                
                folder_url = drive_manager.get_folder_url(folder_id)
                print(f"  Created folder with assessment: {folder_url}")
        else:
            print("No RFPs found to test with")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("\n" + "="*60)
    print("Test complete! Check your Drive folder for results.")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_pdf_downloads()