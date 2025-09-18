#!/usr/bin/env python3
"""
Run discovery for Friday August 15, 2025
(Since weekends have no government RFPs)
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sam_client import SAMClient  
from ai_qualifier import AIQualifier
from sheets_manager import SheetsManager
from drive_manager import DriveManager
from enhanced_discovery import search_broadly, filter_obvious_irrelevant, setup_all_sheets
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def run_friday_discovery():
    """Run discovery for Friday August 15"""
    
    print("\n" + "="*70)
    print("📅 RUNNING DAILY DISCOVERY FOR FRIDAY AUGUST 15, 2025")
    print("="*70)
    print("(Running Friday since weekends have no government RFPs)")
    print("="*70)
    
    # Initialize
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    setup_all_sheets(sheets_manager)
    
    # Friday August 15, 2025
    target_date = '08/15/2025'
    
    print(f"\n🔍 Searching for RFPs from: {target_date}")
    
    # Search broadly
    all_opportunities = search_broadly(sam_client, target_date)
    
    # Filter obvious non-matches
    filtered = filter_obvious_irrelevant(all_opportunities)
    
    # Process all found (no artificial limit)
    to_process = filtered
    
    print(f"\n📊 Found {len(all_opportunities)} total, {len(filtered)} after filtering")
    print(f"🤖 Processing ALL {len(to_process)} RFPs...")
    print("="*70)
    
    # Process all
    all_results = []
    qualified = []
    maybe = []
    rejected = []
    
    for i, opp in enumerate(to_process, 1):
        title = opp.get('title', 'Unknown')[:50]
        
        # Show progress
        if i % 10 == 0:
            print(f"\n[{i}/{len(to_process)}] Processing...")
        
        try:
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            result = {
                'opportunity': opp,
                'assessment': assessment
            }
            
            all_results.append(result)
            
            if score >= 7:
                qualified.append(result)
                print(f"  {i:3}. [{score}/10] ✅ {title}")
            elif score >= 4:
                maybe.append(result)
                print(f"  {i:3}. [{score}/10] 🤔 {title}")
            else:
                rejected.append(result)
                # Only show first 10 rejected
                if len(rejected) <= 10:
                    print(f"  {i:3}. [{score}/10] ❌ {title}")
            
            # Rate limiting
            if i % 20 == 0:
                time.sleep(2)
            else:
                time.sleep(0.3)
                
        except Exception as e:
            logger.error(f"  {i:3}. Error: {str(e)[:50]}")
    
    print("\n" + "="*70)
    
    # Batch write ALL to spam sheet
    if all_results:
        print(f"\n📋 Writing {len(all_results)} RFPs to spam sheet...")
        
        spam_rows = []
        for item in all_results:
            opp = item['opportunity']
            assessment = item['assessment']
            
            spam_rows.append([
                str(assessment.get('relevance_score', 0)),
                '✅' if assessment.get('is_qualified', False) else '🤔' if assessment.get('relevance_score', 0) >= 4 else '❌',
                opp.get('title', '')[:200],
                opp.get('fullParentPathName', '')[:100],
                opp.get('type', ''),
                opp.get('naicsCode', ''),
                opp.get('postedDate', ''),
                opp.get('responseDeadLine', ''),
                assessment.get('justification', '')[:500],
                assessment.get('ai_application', '')[:300] if assessment.get('ai_application') else '',
                ', '.join(assessment.get('similar_past_rfps', [])[:2]) if assessment.get('similar_past_rfps') else '',
                f'=HYPERLINK("{opp.get("uiLink", "")}", "Link")',
                opp.get('noticeId', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M')
            ])
        
        try:
            sheets_manager.service.spreadsheets().values().append(
                spreadsheetId=Config.SPAM_SPREADSHEET_ID,
                range='A:N',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': spam_rows}
            ).execute()
            print(f"  ✓ Added all {len(spam_rows)} to spam sheet")
        except Exception as e:
            logger.error(f"  Error: {str(e)[:100]}")
    
    # Write MAYBE opportunities
    if maybe:
        print(f"\n🤔 Writing {len(maybe)} maybe RFPs...")
        
        maybe_rows = []
        for item in maybe:
            opp = item['opportunity']
            assessment = item['assessment']
            
            maybe_rows.append([
                str(assessment.get('relevance_score', 0)),
                opp.get('title', '')[:200],
                opp.get('fullParentPathName', '')[:100],
                opp.get('type', ''),
                opp.get('naicsCode', ''),
                opp.get('postedDate', ''),
                opp.get('responseDeadLine', ''),
                ', '.join(assessment.get('uncertainty_factors', ['Unclear fit']))[:300],
                assessment.get('justification', '')[:500],
                assessment.get('ai_application', '')[:300] if assessment.get('ai_application') else '',
                f'=HYPERLINK("{opp.get("uiLink", "")}", "Link")',
                opp.get('noticeId', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M')
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
            logger.error(f"  Error: {str(e)[:100]}")
    
    # Process QUALIFIED
    if qualified:
        print(f"\n✅ Processing {len(qualified)} qualified RFPs...")
        
        for item in qualified[:10]:  # Top 10 for main sheet
            opp = item['opportunity']
            assessment = item['assessment']
            
            try:
                folder_name = f"{opp.get('noticeId', '')[:20]} - {opp.get('title', '')[:30]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                folder_url = drive_manager.get_folder_url(folder_id)
                
                sheets_manager.add_opportunity(
                    Config.SPREADSHEET_ID,
                    opp,
                    assessment,
                    folder_url
                )
                
                print(f"  ✓ {opp.get('title', '')[:50]}...")
                
            except Exception as e:
                logger.error(f"  Error: {str(e)[:50]}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 FRIDAY'S DISCOVERY COMPLETE")
    print("="*70)
    print(f"  • Total Evaluated: {len(all_results)}")
    print(f"  • Qualified (7-10): {len(qualified)}")
    print(f"  • Maybe (4-6): {len(maybe)}")
    print(f"  • Rejected (1-3): {len(rejected)}")
    
    if all_results:
        avg = sum(r['assessment'].get('relevance_score', 0) for r in all_results) / len(all_results)
        print(f"  • Average Score: {avg:.1f}/10")
    
    print(f"\n📂 View Results:")
    print(f"  • All RFPs: https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    print(f"  • Maybe: https://docs.google.com/spreadsheets/d/{Config.MAYBE_SPREADSHEET_ID}")
    print(f"  • Qualified: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    
    print("\n✨ Friday's RFPs have been processed!\n")

if __name__ == "__main__":
    run_friday_discovery()