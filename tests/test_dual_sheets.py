#!/usr/bin/env python3
"""
Test dual sheet system - logs ALL RFPs to spam sheet, qualified ones to main sheet
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

def test_dual_sheets():
    print("\n🎯 DUAL SHEET RFP DISCOVERY TEST\n")
    print("=" * 70)
    print(f"📊 Main Sheet (Qualified Only): .../{Config.SPREADSHEET_ID[-6:]}")
    print(f"📋 Spam Sheet (All Evaluated): .../{Config.SPAM_SPREADSHEET_ID[-6:]}")
    print("=" * 70)
    
    # Initialize clients
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Setup spam sheet headers if needed
    print("\n📋 Setting up spam sheet headers...")
    sheets_manager.setup_spam_sheet_headers(Config.SPAM_SPREADSHEET_ID)
    
    # Search last 7 days
    search_from = (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y')
    search_to = datetime.now().strftime('%m/%d/%Y')
    
    print(f"\n🔍 Searching: {search_from} to {search_to}")
    
    # Mix of keywords to get variety of scores
    test_keywords = [
        'artificial intelligence',
        'data processing',
        'software development',
        'construction',  # Should score low
        'facilities',    # Should score low
    ]
    
    all_opportunities = []
    
    print("\n📡 Fetching RFPs from SAM.gov...\n")
    for keyword in test_keywords:
        print(f"  • {keyword}...", end=" ")
        try:
            opps = sam_client.search_by_keyword(keyword, search_from, search_to)
            print(f"Found {len(opps)}")
            # Take first 3 from each keyword
            all_opportunities.extend(opps[:3])
        except Exception as e:
            print(f"Error: {str(e)[:30]}")
    
    # Deduplicate
    unique = {}
    for opp in all_opportunities:
        if opp.get('noticeId') not in unique:
            unique[opp['noticeId']] = opp
    
    print(f"\n📊 Found {len(unique)} unique opportunities to evaluate")
    print("=" * 70)
    
    # Process up to 10
    test_batch = list(unique.items())[:10]
    
    print(f"\n🤖 EVALUATING {len(test_batch)} RFPs WITH AI...\n")
    
    qualified_count = 0
    all_scores = []
    
    for i, (notice_id, opp) in enumerate(test_batch, 1):
        title = opp.get('title', 'Unknown')[:60]
        print(f"{i:2}. {title}...")
        
        try:
            # Evaluate with AI
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            is_qualified = assessment.get('is_qualified', False)
            all_scores.append(score)
            
            # Add to spam sheet (ALL evaluated RFPs)
            print(f"    Score: {score}/10", end="")
            sheets_manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, opp, assessment)
            print(" → Added to spam sheet", end="")
            
            # If qualified, also add to main sheet and create Drive folder
            if is_qualified:
                qualified_count += 1
                print(" ✅ QUALIFIED!", end="")
                
                # Create Drive folder for qualified ones
                folder_name = f"{notice_id[:15]} - {title[:30]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                
                # Create simple report
                report = f"""QUALIFIED OPPORTUNITY
Score: {score}/10

{opp.get('title', 'N/A')}
{opp.get('fullParentPathName', 'N/A')}

Why Qualified:
{assessment.get('justification', 'N/A')}

AI Application:
{assessment.get('ai_application', 'N/A')}
"""
                drive_manager.upload_file(
                    report.encode('utf-8'),
                    'assessment.txt',
                    folder_id,
                    'text/plain'
                )
                
                folder_url = drive_manager.get_folder_url(folder_id)
                
                # Add to main sheet
                if Config.SPREADSHEET_ID:
                    sheets_manager.add_opportunity(
                        Config.SPREADSHEET_ID,
                        opp,
                        assessment,
                        folder_url
                    )
                    print(" → Added to main sheet")
                else:
                    print()
            else:
                print(" ❌ Not qualified")
            
            # Small delay to avoid rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    ⚠️ Error: {str(e)[:50]}")
            all_scores.append(0)
    
    # Summary
    print("\n" + "=" * 70)
    print("\n📊 EVALUATION SUMMARY:\n")
    print(f"  • Total Evaluated: {len(test_batch)}")
    print(f"  • Qualified (7-10): {qualified_count}")
    print(f"  • Not Qualified (1-6): {len(test_batch) - qualified_count}")
    
    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)
        print(f"  • Average Score: {avg_score:.1f}/10")
        print(f"  • Score Range: {min(all_scores)}-{max(all_scores)}/10")
    
    print("\n📋 VIEW RESULTS:\n")
    print(f"  • ALL RFPs with scores (spam sheet):")
    print(f"    https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    print(f"\n  • QUALIFIED RFPs only (main sheet):")
    print(f"    https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    print(f"\n  • Drive folder with assessments:")
    print(f"    https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
    
    print("\n✨ DUAL SHEET TEST COMPLETE!\n")
    print("Check the spam sheet to see ALL evaluated RFPs with their scores 1-10.")
    print("The main sheet contains only qualified opportunities (score ≥ 6).\n")

if __name__ == "__main__":
    test_dual_sheets()