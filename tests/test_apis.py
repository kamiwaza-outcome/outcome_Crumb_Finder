#!/usr/bin/env python3
"""Test Google APIs access"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

def test_apis():
    print("Testing Google APIs access...")
    
    # Load credentials
    creds_path = '/Users/finnegannorris/Downloads/rfp-discovery-system-e67dc59c8ee1.json'
    
    with open(creds_path) as f:
        creds_data = json.load(f)
        print(f"Project ID: {creds_data.get('project_id')}")
        print(f"Service Account: {creds_data.get('client_email')}")
    
    try:
        # Create credentials with both scopes
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=[
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
        )
        
        # Test Drive API
        print("\n1. Testing Drive API...")
        drive_service = build('drive', 'v3', credentials=creds)
        
        # List files (should work even if empty)
        results = drive_service.files().list(pageSize=1).execute()
        print("   ✓ Drive API is working")
        
        # Test Sheets API
        print("\n2. Testing Sheets API...")
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Try to create a test spreadsheet
        spreadsheet = {
            'properties': {
                'title': 'RFP Test Sheet - Delete Me'
            }
        }
        
        sheet = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        sheet_id = sheet.get('spreadsheetId')
        print(f"   ✓ Successfully created test sheet: {sheet_id}")
        print(f"   URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
        
        # Clean up - delete the test sheet
        drive_service.files().delete(fileId=sheet_id).execute()
        print("   ✓ Deleted test sheet")
        
        print("\n✅ All APIs are working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
        # Check if it's a permission error
        if "403" in str(e):
            print("\nPossible issues:")
            print("1. Make sure both Google Drive API and Google Sheets API are enabled")
            print("2. Go to: https://console.cloud.google.com/apis/library")
            print("3. Search for and enable both APIs for your project")
            print("4. Wait a minute for changes to propagate")
        
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_apis()