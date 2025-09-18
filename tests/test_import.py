#!/usr/bin/env python3
"""
Test script for RFP import functionality
Run this to test importing an RFP without Slack
"""

import sys
import logging
from import_rfp import RFPImporter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Test the import functionality"""
    
    # Example SAM.gov URLs for testing
    test_urls = [
        "https://sam.gov/opp/ffc7d69492944cb499af62babcaa6ed8/view",  # Example from your data
        "https://sam.gov/opp/abc123def456/view",  # Fake URL for testing
    ]
    
    print("=" * 60)
    print("RFP IMPORT TEST")
    print("=" * 60)
    print()
    
    # Get URL from command line or use test URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Testing with provided URL: {url}")
    else:
        url = input("Enter SAM.gov URL (or press Enter for test URL): ").strip()
        if not url:
            url = test_urls[0]
            print(f"Using test URL: {url}")
    
    print()
    
    # Initialize importer
    print("Initializing importer...")
    importer = RFPImporter()
    
    # Test URL extraction
    print("\n1. Testing URL extraction...")
    notice_id = importer.extract_notice_id(url)
    if notice_id:
        print(f"   ✓ Extracted notice ID: {notice_id}")
    else:
        print(f"   ✗ Failed to extract notice ID from URL")
        return
    
    # Test duplicate checking
    print("\n2. Checking for existing RFP...")
    existing = importer.check_existing_rfp(notice_id)
    if existing['exists']:
        print(f"   ℹ️  RFP exists in {existing['sheet_name']} sheet (Row {existing['row']})")
        print(f"   Status: {existing['status']}")
        print(f"   AI Score: {existing['ai_score']}")
    else:
        print(f"   ✓ RFP not found in any sheet")
    
    # Ask if we should proceed with import
    print("\n3. Import Decision")
    if existing['exists'] and existing['sheet_name'] == 'Main':
        print("   ⚠️  RFP already in Main sheet - import will be skipped")
        proceed = False
    else:
        proceed = input("   Proceed with import? (y/n): ").lower() == 'y'
    
    if proceed:
        print("\n4. Importing RFP...")
        result = importer.import_rfp(url, user="Test User")
        
        print("\n" + "=" * 60)
        print("IMPORT RESULT:")
        print("=" * 60)
        print(result['message'])
        
        if result['success']:
            print("\n✅ Import successful!")
            print(f"   Row: {result['row']}")
            print(f"   Notice ID: {result['notice_id']}")
            if result['details']:
                print(f"   Title: {result['details'].get('title', 'N/A')}")
                print(f"   Agency: {result['details'].get('agency', 'N/A')}")
                print(f"   AI Score: {result['details'].get('ai_score', 'N/A')}")
        else:
            print("\n❌ Import failed")
    else:
        print("\n   Import cancelled")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()