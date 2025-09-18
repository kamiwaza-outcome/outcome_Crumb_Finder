#!/usr/bin/env python3
"""Show all unique dates in the main sheet"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sheets_manager import SheetsManager
from collections import defaultdict

sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)

# Get formatted values to see dates
result = sheets_manager.service.spreadsheets().values().get(
    spreadsheetId=Config.SPREADSHEET_ID,
    range='Sheet1!A:T',
    valueRenderOption='FORMATTED_VALUE'
).execute()

values = result.get('values', [])

if not values:
    print("No data found")
    exit()

# Count dates in column T (index 19)
date_counts = defaultdict(int)
for row_num in range(1, len(values)):
    row = values[row_num]
    if len(row) > 19:
        date_value = row[19]
        if date_value:
            date_counts[date_value] += 1

print(f"Found {len(date_counts)} unique dates:")
print(f"Total rows with dates: {sum(date_counts.values())}")
print("\nDates and counts:")
for date, count in sorted(date_counts.items(), reverse=True)[:20]:
    print(f"  {date}: {count} RFPs")