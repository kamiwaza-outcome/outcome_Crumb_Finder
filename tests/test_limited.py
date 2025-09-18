#!/usr/bin/env python3
"""
Limited test of RFP Discovery System - processes small batch to avoid rate limits
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from config import Config
from sam_client import SAMClient  
from ai_qualifier import AIQualifier
from drive_manager import DriveManager
from sheets_manager import SheetsManager

def test_limited_rfps():
    print("\n🚀 RFP DISCOVERY SYSTEM - LIMITED TEST\n")
    print("=" * 70)
    
    # Initialize clients
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Search last 7 days to get more results
    search_from = (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y')
    search_to = datetime.now().strftime('%m/%d/%Y')
    
    print(f"📅 Searching: {search_from} to {search_to}\n")
    
    # LIMITED keywords for testing
    test_keywords = [
        'artificial intelligence',
        'machine learning',
        'data analytics'
    ]
    
    all_opportunities = []
    
    print("🔍 Searching SAM.gov (LIMITED TEST)...\n")
    for keyword in test_keywords:
        print(f"  Searching: {keyword}...", end=" ")
        try:
            opps = sam_client.search_by_keyword(keyword, search_from, search_to)
            print(f"Found {len(opps)}")
            all_opportunities.extend(opps[:20])  # Limit each search to 20 results
        except Exception as e:
            print(f"Error: {str(e)[:50]}")
    
    # Deduplicate
    unique = {}
    for opp in all_opportunities:
        if opp.get('noticeId') not in unique:
            unique[opp['noticeId']] = opp
    
    print(f"\n📊 Found {len(unique)} unique opportunities (limiting to 5 for test)\n")
    print("=" * 70)
    
    # Process only first 5 for testing
    test_batch = list(unique.items())[:5]
    
    # Check for existing entries in sheet (with rate limit handling)
    existing_notice_ids = set()
    if Config.SPREADSHEET_ID:
        print("\n📋 Checking for duplicates in spreadsheet...")
        try:
            existing_notice_ids = set(sheets_manager.get_all_notice_ids(Config.SPREADSHEET_ID))
            print(f"   Found {len(existing_notice_ids)} existing entries\n")
        except Exception as e:
            print(f"   Could not check duplicates: {str(e)[:50]}\n")
    
    # Evaluate with AI
    print("🤖 EVALUATING WITH GPT-4o...\n")
    
    qualified = []
    for i, (notice_id, opp) in enumerate(test_batch, 1):
        # Skip if already in sheet
        if notice_id in existing_notice_ids:
            print(f"\n{i}. {opp.get('title', 'Unknown')[:60]}...")
            print(f"   ⏭️ Already in spreadsheet, skipping")
            continue
            
        print(f"\n{i}. {opp.get('title', 'Unknown')[:60]}...")
        print(f"   Agency: {opp.get('fullParentPathName', 'Unknown')[:50]}")
        print(f"   Posted: {opp.get('postedDate', 'Unknown')}")
        print(f"   Deadline: {opp.get('responseDeadLine', 'Not specified')}")
        
        try:
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            print(f"   Score: {score}/10", end=" - ")
            
            if assessment.get('is_qualified'):
                print("✅ QUALIFIED FOR COMPANY")
                print(f"   Why: {assessment.get('justification', '')[:150]}...")
                print(f"   AI Use: {assessment.get('ai_application', '')[:100]}...")
                
                qualified.append({
                    'opportunity': opp,
                    'assessment': assessment
                })
            else:
                print("❌ Not a fit")
                print(f"   Reason: {assessment.get('justification', '')[:100]}...")
                
        except Exception as e:
            print(f"   ⚠️ Error: {str(e)[:100]}")
    
    print("\n" + "=" * 70)
    print(f"\n🎯 RESULTS: {len(qualified)} qualified opportunities for Test Company\n")
    
    # Store in Google Drive and Sheets
    if qualified:
        if Config.GOOGLE_DRIVE_FOLDER_ID:
            print("📁 Storing in Google Drive...")
            
            for item in qualified:
                opp = item['opportunity']
                assessment = item['assessment']
                
                try:
                    # Create folder
                    folder_name = f"{opp.get('noticeId', 'Unknown')[:20]} - {opp.get('title', 'Unknown')[:40]}"
                    folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                    
                    # Create summary report
                    report = f"""COMPANY OPPORTUNITY ASSESSMENT
{'='*40}

Title: {opp.get('title', 'N/A')}
Agency: {opp.get('fullParentPathName', 'N/A')}
Notice ID: {opp.get('noticeId', 'N/A')}
Deadline: {opp.get('responseDeadLine', 'N/A')}

AI SCORE: {assessment.get('relevance_score', 0)}/10

WHY THIS FITS THE COMPANY:
{assessment.get('justification', 'N/A')}

HOW THE COMPANY'S PLATFORM APPLIES:
{assessment.get('ai_application', 'N/A')}

SIMILAR PAST WINS:
{', '.join(assessment.get('similar_past_rfps', [])) or 'None identified'}

SUGGESTED APPROACH:
{assessment.get('suggested_approach', 'N/A')}

SAM.gov Link: {opp.get('uiLink', 'N/A')}
"""
                    
                    # Upload report
                    drive_manager.upload_file(
                        report.encode('utf-8'),
                        'company_assessment.txt',
                        folder_id,
                        'text/plain'
                    )
                    
                    folder_url = drive_manager.get_folder_url(folder_id)
                    print(f"   ✓ Stored: {opp.get('title', '')[:50]}")
                    
                    # Add to spreadsheet
                    if Config.SPREADSHEET_ID:
                        print(f"   📊 Adding to spreadsheet...", end=" ")
                        try:
                            sheets_manager.add_opportunity(
                                Config.SPREADSHEET_ID,
                                opp,
                                assessment,
                                folder_url
                            )
                            print("Done")
                            time.sleep(1)  # Small delay to avoid rate limits
                        except Exception as e:
                            print(f"Failed: {str(e)[:50]}")
                    
                except Exception as e:
                    print(f"   ⚠️ Error: {str(e)[:100]}")
        
        print(f"\n📂 View opportunities in Drive:")
        print(f"   https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
        
        if Config.SPREADSHEET_ID:
            print(f"\n📊 View tracking spreadsheet:")
            print(f"   https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    else:
        print("No new qualified opportunities found in this test batch.")
        print("This is normal - not all RFPs match the company's capabilities.")
    
    print("\n✨ TEST COMPLETE!\n")

if __name__ == "__main__":
    test_limited_rfps()