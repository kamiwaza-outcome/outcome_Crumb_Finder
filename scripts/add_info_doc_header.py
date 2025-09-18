#!/usr/bin/env python3
"""
Add Info Doc header to the main sheet
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sheets_manager import SheetsManager

def main():
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Update cell S1 with "Info Doc" header
    sheets_manager.service.spreadsheets().values().update(
        spreadsheetId=Config.SPREADSHEET_ID,
        range='Sheet1!S1',
        valueInputOption='USER_ENTERED',
        body={'values': [['Info Doc']]}
    ).execute()
    
    print("✅ Added 'Info Doc' header to column S")

if __name__ == "__main__":
    main()