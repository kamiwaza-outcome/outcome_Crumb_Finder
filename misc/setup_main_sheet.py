#!/usr/bin/env python3
"""
Setup the main sheet with proper headers and formatting
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sheets_manager import SheetsManager

def setup_main_sheet():
    print("\n🔧 SETTING UP MAIN SHEET FOR QUALIFIED RFPS\n")
    print("=" * 60)
    
    if not Config.SPREADSHEET_ID:
        print("❌ No main sheet ID configured in .env")
        return
    
    print(f"📊 Sheet ID: {Config.SPREADSHEET_ID}")
    print(f"📋 URL: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}\n")
    
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    try:
        # First, check what sheets exist
        spreadsheet = sheets_manager.service.spreadsheets().get(
            spreadsheetId=Config.SPREADSHEET_ID
        ).execute()
        
        existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])]
        print(f"Existing sheets: {', '.join(existing_sheets)}\n")
        
        # Check if the first sheet needs headers (we'll use the first sheet)
        first_sheet = existing_sheets[0] if existing_sheets else None
        
        if first_sheet:
            print(f"Using sheet: '{first_sheet}'")
            
            # Check if headers already exist
            try:
                result = sheets_manager.service.spreadsheets().values().get(
                    spreadsheetId=Config.SPREADSHEET_ID,
                    range=f'{first_sheet}!A1:S1'
                ).execute()
                
                if result.get('values'):
                    print("✓ Headers already exist")
                else:
                    print("Adding headers...")
                    # Add headers
                    headers = [[
                        'AI Recommended',
                        'Human Review',
                        'Status',
                        'Response Deadline',
                        'Notice ID',
                        'Solicitation Number',
                        'Title',
                        'Agency',
                        'NAICS',
                        'PSC',
                        'Posted Date',
                        'SAM.gov Link',
                        'Drive Folder',
                        'AI Score',
                        'AI Justification',
                        'Key Requirements',
                        'Suggested Approach',
                        'AI Application',
                        'Date Added'
                    ]]
                    
                    sheets_manager.service.spreadsheets().values().update(
                        spreadsheetId=Config.SPREADSHEET_ID,
                        range=f'{first_sheet}!A1:S1',
                        valueInputOption='USER_ENTERED',
                        body={'values': headers}
                    ).execute()
                    
                    # Format header row
                    sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']
                    
                    requests = [{
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 0,
                                'endRowIndex': 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'textFormat': {'bold': True, 'fontSize': 11},
                                    'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.8},
                                    'horizontalAlignment': 'CENTER',
                                    'textColor': {'red': 1, 'green': 1, 'blue': 1}
                                }
                            },
                            'fields': 'userEnteredFormat'
                        }
                    }]
                    
                    sheets_manager.service.spreadsheets().batchUpdate(
                        spreadsheetId=Config.SPREADSHEET_ID,
                        body={'requests': requests}
                    ).execute()
                    
                    print("✓ Headers added and formatted")
                    
            except Exception as e:
                print(f"Warning: {str(e)[:100]}")
            
            # Update config to use the first sheet name
            print(f"\n📝 Note: Update your sheets_manager.py to use '{first_sheet}' instead of 'Opportunities'")
            print(f"   Or rename your sheet tab to 'Opportunities'\n")
            
        print("✅ Main sheet is ready!")
        print("\nNext steps:")
        print("1. Run the discovery script again")
        print("2. Qualified RFPs (7+/10) will appear in the main sheet")
        print("3. ALL RFPs will continue to appear in the spam sheet")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nPlease make sure:")
        print("1. The sheet ID is correct")
        print("2. The service account has access to the sheet")

if __name__ == "__main__":
    setup_main_sheet()