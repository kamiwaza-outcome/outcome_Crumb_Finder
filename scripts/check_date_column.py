#!/usr/bin/env python3
"""Check what's in the Date Added column"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.sheets_manager import SheetsManager

sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)

# Get both formula and formatted values
formula_result = sheets_manager.service.spreadsheets().values().get(
    spreadsheetId=Config.SPREADSHEET_ID,
    range='Sheet1!S:T',  # Just columns S and T
    valueRenderOption='FORMULA'
).execute()

formatted_result = sheets_manager.service.spreadsheets().values().get(
    spreadsheetId=Config.SPREADSHEET_ID,
    range='Sheet1!S:T',  # Just columns S and T
    valueRenderOption='FORMATTED_VALUE'
).execute()

formula_values = formula_result.get('values', [])
formatted_values = formatted_result.get('values', [])

print(f"Total rows: {len(formula_values)}")
print("\nFirst 10 rows of columns S and T:")
print("Row | Column S (Info Doc) | Column T (Date Added)")
print("-" * 60)

for i in range(min(10, len(formula_values))):
    formula_row = formula_values[i] if i < len(formula_values) else []
    formatted_row = formatted_values[i] if i < len(formatted_values) else []
    
    col_s_formula = formula_row[0] if len(formula_row) > 0 else ''
    col_t_formula = formula_row[1] if len(formula_row) > 1 else ''
    col_s_formatted = formatted_row[0] if len(formatted_row) > 0 else ''
    col_t_formatted = formatted_row[1] if len(formatted_row) > 1 else ''
    
    print(f"{i+1:3} | S: {col_s_formatted[:30]:<30} | T: {col_t_formatted}")
    if 'HYPERLINK' in str(col_s_formula):
        print(f"    | (has HYPERLINK formula)")

print("\nLast 50 rows with data in column T:")
for i in range(max(0, len(formatted_values) - 50), len(formatted_values)):
    if i < len(formatted_values):
        formatted_row = formatted_values[i]
        if len(formatted_row) > 1 and formatted_row[1]:  # Has value in column T
            print(f"Row {i+1}: {formatted_row[1]}")