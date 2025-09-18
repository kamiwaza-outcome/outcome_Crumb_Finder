#!/usr/bin/env python3
"""
Test RFP discovery without Google Sheets
Just finds RFPs and stores them in Drive
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from sam_client import SAMClient
from ai_qualifier import AIQualifier
from drive_manager import DriveManager

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def test_rfp_discovery():
    """Test RFP discovery without sheets"""
    
    print("\n🔍 Starting RFP Discovery Test (Without Sheets)\n")
    print("=" * 60)
    
    # Initialize clients
    print("Initializing clients...")
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Search parameters - use wider range to ensure we get results
    # Search last 7 days to ensure we find something
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y')
    today = datetime.now().strftime('%m/%d/%Y')
    
    print(f"Searching for RFPs posted between {week_ago} and {today}")
    print("-" * 60)
    
    # Search with limited keywords for testing
    all_opportunities = []
    
    # Test with just a few keywords
    test_keywords = ['artificial intelligence', 'machine learning', 'data analytics']
    
    for keyword in test_keywords:
        print(f"\n📌 Searching for: {keyword}")
        opportunities = sam_client.search_by_keyword(keyword, week_ago, today)
        print(f"   Found {len(opportunities)} opportunities")
        all_opportunities.extend(opportunities)
    
    # Deduplicate
    unique_opps = {}
    for opp in all_opportunities:
        notice_id = opp.get('noticeId')
        if notice_id and notice_id not in unique_opps:
            unique_opps[notice_id] = opp
    
    print(f"\n📊 Total unique opportunities found: {len(unique_opps)}")
    print("=" * 60)
    
    # Evaluate with AI
    qualified = []
    print("\n🤖 Evaluating opportunities with GPT-5...\n")
    
    for i, (notice_id, opp) in enumerate(list(unique_opps.items())[:5], 1):  # Limit to 5 for testing
        print(f"{i}. {opp.get('title', 'Unknown')[:80]}...")
        print(f"   Agency: {opp.get('fullParentPathName', 'Unknown')}")
        print(f"   Notice ID: {notice_id}")
        
        try:
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            if assessment.get('is_qualified'):
                print(f"   ✅ QUALIFIED (Score: {score}/10)")
                print(f"   Justification: {assessment.get('justification', '')[:100]}...")
                qualified.append({
                    'opportunity': opp,
                    'assessment': assessment
                })
            else:
                print(f"   ❌ Not qualified (Score: {score}/10)")
                
        except Exception as e:
            print(f"   ⚠️ Error evaluating: {str(e)[:100]}")
        
        print()
    
    print("=" * 60)
    print(f"\n🎯 Results: {len(qualified)} qualified opportunities out of {min(5, len(unique_opps))} evaluated")
    
    # Store qualified opportunities in Drive
    if qualified and Config.GOOGLE_DRIVE_FOLDER_ID:
        print("\n📁 Storing qualified opportunities in Google Drive...")
        
        for item in qualified:
            opp = item['opportunity']
            assessment = item['assessment']
            
            try:
                # Create folder for this opportunity
                folder_name = f"{opp.get('noticeId', 'Unknown')} - {opp.get('title', 'Unknown')[:50]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                
                # Store summary
                summary = f"""
RFP OPPORTUNITY ASSESSMENT
==========================
Title: {opp.get('title', 'N/A')}
Agency: {opp.get('fullParentPathName', 'N/A')}
Notice ID: {opp.get('noticeId', 'N/A')}
Response Deadline: {opp.get('responseDeadLine', 'N/A')}

AI ASSESSMENT
Score: {assessment.get('relevance_score', 0)}/10
Qualified: {'Yes' if assessment.get('is_qualified') else 'No'}

Justification:
{assessment.get('justification', 'N/A')}

Key Requirements:
{', '.join(assessment.get('key_requirements', []))}

Suggested Approach:
{assessment.get('suggested_approach', 'N/A')}

AI Application:
{assessment.get('ai_application', 'N/A')}

SAM.gov Link: {opp.get('uiLink', 'N/A')}
"""
                
                drive_manager.upload_file(
                    summary.encode('utf-8'),
                    'assessment.txt',
                    folder_id,
                    'text/plain'
                )
                
                folder_url = drive_manager.get_folder_url(folder_id)
                print(f"   ✓ Stored: {opp.get('title', '')[:50]}...")
                print(f"     Folder: {folder_url}")
                
            except Exception as e:
                print(f"   ⚠️ Error storing: {str(e)[:100]}")
    
    print("\n✅ Test complete!")
    print("\nNote: To enable full functionality with Google Sheets tracking:")
    print("1. Enable Google Sheets API in your Google Cloud Console")
    print("2. Or create a sheet manually and provide its ID")

if __name__ == "__main__":
    test_rfp_discovery()