#!/usr/bin/env python3
"""
Manual setup helper - creates the tracking sheet manually
"""

print("""
📋 MANUAL SETUP REQUIRED
========================

Since the Sheets API isn't enabled properly, please:

1. Go to Google Sheets: https://sheets.google.com/

2. Create a new spreadsheet called "RFP Opportunities Tracker"

3. Share it with this email:
   rfp-discovery-bot@rfp-discovery-system.iam.gserviceaccount.com
   (Give it "Editor" permission)

4. Copy the sheet ID from the URL:
   - The URL will look like: https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
   - Copy the SHEET_ID_HERE part

5. Run this command with your sheet ID:
   python main.py --test --sheet-id YOUR_SHEET_ID

Alternatively, to fix the API issue:
1. Go to: https://console.cloud.google.com/apis/library?project=rfp-discovery-system
2. Search for "Google Sheets API"
3. Click on it and press "ENABLE"
4. Wait 2-3 minutes for it to activate

Note: The Drive API is working fine, so we can still store documents!
""")