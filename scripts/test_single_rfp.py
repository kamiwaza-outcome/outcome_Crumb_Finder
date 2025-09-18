#!/usr/bin/env python3
"""Test processing a single RFP"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.drive_manager import DriveManager
from src.sam_client import SAMClient

# Test with the RFI AI + DPA RFP
notice_id = '7e833ee2047242faa81f996e1ad80b29'
folder_id = '1Q65_aNajRrBl5Gn_SgRsn1esBbcL2Lfo'  # Get this from the Drive link

drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
sam_client = SAMClient(Config.SAM_API_KEY)

print(f"Getting RFP details for {notice_id}...")

# Get RFP details
params = {
    'api_key': sam_client.api_key,
    'noticeId': notice_id,
    'limit': 1
}

response = sam_client._make_request(params)
if response and 'opportunitiesData' in response:
    opportunities = response.get('opportunitiesData', [])
    if opportunities:
        opportunity = opportunities[0]
        print(f"Found: {opportunity.get('title', 'Unknown')}")
        
        # Create comprehensive info doc
        print("Creating comprehensive info document...")
        info_doc_link = drive_manager.create_info_document(opportunity, folder_id)
        
        if info_doc_link:
            print(f"✅ Created info doc: {info_doc_link}")
        else:
            print("❌ Failed to create info doc")
    else:
        print("No opportunity found")
else:
    print("Failed to get RFP details")