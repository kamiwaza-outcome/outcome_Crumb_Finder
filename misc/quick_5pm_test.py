#!/usr/bin/env python3
"""
Quick test of what happens at 5pm - simulates daily run with limited batch
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sam_client import SAMClient  
from ai_qualifier import AIQualifier
from sheets_manager import SheetsManager
from drive_manager import DriveManager

def simulate_5pm_run():
    """Simulate what happens at 5pm daily run"""
    
    print("\n" + "="*70)
    print("⏰ SIMULATING 5PM DAILY RUN")
    print("="*70)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This simulates what would happen at 5:00 PM Eastern daily")
    print("="*70)
    
    # Initialize
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # In production, this would be yesterday
    # For testing, using today
    target_date = datetime.now().strftime('%m/%d/%Y')
    print(f"\n📅 Searching for RFPs from: {target_date}")
    print("(In production this would be yesterday)")
    
    # Quick search - just NAICS codes for speed
    print("\n🔍 Searching SAM.gov...")
    all_opportunities = []
    
    naics_codes = ['541511', '541512', '541519']  # Just 3 for quick test
    
    for naics in naics_codes:
        try:
            opps = sam_client.search_by_naics(naics, target_date, target_date)
            all_opportunities.extend(opps[:3])  # Limit each to 3
            print(f"  NAICS {naics}: Found {len(opps)}, taking first 3")
            time.sleep(0.5)
        except Exception as e:
            print(f"  NAICS {naics}: Error - {str(e)[:50]}")
    
    # Deduplicate
    unique = {}
    for opp in all_opportunities:
        if opp.get('noticeId') not in unique:
            unique[opp['noticeId']] = opp
    
    to_process = list(unique.values())[:5]  # Just 5 for quick test
    
    print(f"\n📊 Processing {len(to_process)} RFPs")
    print("="*70)
    
    # Process with AI
    all_results = []
    qualified = []
    maybe = []
    rejected = []
    
    print("\n🤖 AI EVALUATION:")
    for i, opp in enumerate(to_process, 1):
        title = opp.get('title', 'Unknown')[:50]
        
        try:
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            result = {'opportunity': opp, 'assessment': assessment}
            all_results.append(result)
            
            if score >= 7:
                qualified.append(result)
                print(f"  {i}. [{score}/10] ✅ {title}")
            elif score >= 4:
                maybe.append(result)
                print(f"  {i}. [{score}/10] 🤔 {title}")
            else:
                rejected.append(result)
                print(f"  {i}. [{score}/10] ❌ {title}")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  {i}. Error: {str(e)[:50]}")
    
    print("\n" + "="*70)
    print("📝 WRITING TO SHEETS:")
    
    # Write to spam sheet (all RFPs)
    if all_results:
        spam_rows = []
        for item in all_results:
            opp = item['opportunity']
            assessment = item['assessment']
            
            spam_rows.append([
                str(assessment.get('relevance_score', 0)),
                '✅' if score >= 7 else '🤔' if score >= 4 else '❌',
                opp.get('title', '')[:150],
                opp.get('fullParentPathName', '')[:80],
                opp.get('type', ''),
                opp.get('naicsCode', ''),
                opp.get('postedDate', ''),
                opp.get('responseDeadLine', '')[:20],
                assessment.get('justification', '')[:300],
                assessment.get('ai_application', '')[:200] if assessment.get('ai_application') else '',
                '', # similar RFPs
                f'=HYPERLINK("{opp.get("uiLink", "")}", "Link")',
                opp.get('noticeId', ''),
                datetime.now().strftime('%H:%M')
            ])
        
        try:
            sheets_manager.service.spreadsheets().values().append(
                spreadsheetId=Config.SPAM_SPREADSHEET_ID,
                range='A:N',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': spam_rows}
            ).execute()
            print(f"  ✓ Added {len(spam_rows)} to spam sheet")
        except Exception as e:
            print(f"  ❌ Spam sheet error: {str(e)[:50]}")
    
    # Write to maybe sheet
    if maybe:
        maybe_rows = []
        for item in maybe:
            opp = item['opportunity']
            assessment = item['assessment']
            
            maybe_rows.append([
                str(assessment.get('relevance_score', 0)),
                opp.get('title', '')[:150],
                opp.get('fullParentPathName', '')[:80],
                opp.get('type', ''),
                opp.get('naicsCode', ''),
                opp.get('postedDate', ''),
                opp.get('responseDeadLine', '')[:20],
                'Unclear fit - needs review',
                assessment.get('justification', '')[:300],
                assessment.get('ai_application', '')[:200] if assessment.get('ai_application') else '',
                f'=HYPERLINK("{opp.get("uiLink", "")}", "Link")',
                opp.get('noticeId', ''),
                datetime.now().strftime('%H:%M')
            ])
        
        try:
            sheets_manager.service.spreadsheets().values().append(
                spreadsheetId=Config.MAYBE_SPREADSHEET_ID,
                range='A:M',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': maybe_rows}
            ).execute()
            print(f"  ✓ Added {len(maybe_rows)} to maybe sheet")
        except Exception as e:
            print(f"  ❌ Maybe sheet error: {str(e)[:50]}")
    
    # Process qualified
    if qualified:
        for item in qualified[:2]:  # Just first 2
            opp = item['opportunity']
            assessment = item['assessment']
            
            try:
                # Create Drive folder
                folder_name = f"{opp.get('noticeId', '')[:15]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                folder_url = drive_manager.get_folder_url(folder_id)
                
                # Add to main sheet
                sheets_manager.add_opportunity(
                    Config.SPREADSHEET_ID,
                    opp,
                    assessment,
                    folder_url
                )
                
                print(f"  ✓ Added qualified RFP to main sheet")
                
            except Exception as e:
                print(f"  ❌ Main sheet error: {str(e)[:50]}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 5PM RUN COMPLETE - SUMMARY")
    print("="*70)
    print(f"  • Total Evaluated: {len(all_results)}")
    print(f"  • Qualified (7-10): {len(qualified)} → Main sheet")
    print(f"  • Maybe (4-6): {len(maybe)} → Review sheet")
    print(f"  • Rejected (1-3): {len(rejected)} → Spam sheet only")
    
    print(f"\n📂 Check your sheets:")
    print(f"  • All RFPs: https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    print(f"  • Maybe: https://docs.google.com/spreadsheets/d/{Config.MAYBE_SPREADSHEET_ID}")
    print(f"  • Qualified: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    
    print("\n✅ Daily run simulation complete!")
    print("In production, this would run automatically at 5:00 PM Eastern.\n")
    
    return len(all_results)

if __name__ == "__main__":
    simulate_5pm_run()