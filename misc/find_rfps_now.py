#!/usr/bin/env python3
"""
Find and evaluate RFPs right now - simplified version
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from config import Config
from sam_client import SAMClient  
from ai_qualifier import AIQualifier
from drive_manager import DriveManager

def find_rfps():
    print("\n🚀 RFP DISCOVERY SYSTEM - FINDING AI OPPORTUNITIES\n")
    print("=" * 70)
    
    # Initialize clients
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Search last 3 days
    search_from = (datetime.now() - timedelta(days=3)).strftime('%m/%d/%Y')
    search_to = datetime.now().strftime('%m/%d/%Y')
    
    print(f"📅 Searching: {search_from} to {search_to}\n")
    
    all_opportunities = []
    
    # Search with AI-related keywords
    keywords = [
        'artificial intelligence',
        'machine learning', 
        'data analytics',
        'automation',
        'software development',
        'cloud computing'
    ]
    
    print("🔍 Searching SAM.gov...\n")
    for keyword in keywords:
        print(f"  Searching: {keyword}...", end=" ")
        try:
            opps = sam_client.search_by_keyword(keyword, search_from, search_to)
            print(f"Found {len(opps)}")
            all_opportunities.extend(opps)
        except Exception as e:
            print(f"Error: {str(e)[:50]}")
    
    # Deduplicate
    unique = {}
    for opp in all_opportunities:
        if opp.get('noticeId') not in unique:
            unique[opp['noticeId']] = opp
    
    print(f"\n📊 Found {len(unique)} unique opportunities\n")
    print("=" * 70)
    
    # Evaluate with AI
    print("\n🤖 EVALUATING WITH GPT-5...\n")
    
    qualified = []
    for i, (notice_id, opp) in enumerate(list(unique.items())[:10], 1):  # Limit to 10
        print(f"\n{i}. {opp.get('title', 'Unknown')[:70]}...")
        print(f"   Agency: {opp.get('fullParentPathName', 'Unknown')[:50]}")
        print(f"   Posted: {opp.get('postedDate', 'Unknown')}")
        print(f"   Deadline: {opp.get('responseDeadLine', 'Not specified')}")
        
        try:
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            print(f"   Score: {score}/10", end=" - ")
            
            if assessment.get('is_qualified'):
                print(f"✅ QUALIFIED FOR {Config.get_company_name()}")
                print(f"   Why: {assessment.get('justification', '')[:150]}...")
                print(f"   AI Use: {assessment.get('ai_application', '')[:100]}...")
                
                qualified.append({
                    'opportunity': opp,
                    'assessment': assessment
                })
            else:
                print("❌ Not a fit")
                
        except Exception as e:
            print(f"   ⚠️ Error: {str(e)[:50]}")
    
    print("\n" + "=" * 70)
    print(f"\n🎯 RESULTS: {len(qualified)} qualified opportunities for {Config.get_company_name()}\n")
    
    # Store in Drive
    if qualified and Config.GOOGLE_DRIVE_FOLDER_ID:
        print("📁 Storing in Google Drive...\n")
        
        for item in qualified[:5]:  # Store top 5
            opp = item['opportunity']
            assessment = item['assessment']
            
            try:
                # Create folder
                folder_name = f"{opp.get('noticeId', 'Unknown')[:20]} - {opp.get('title', 'Unknown')[:40]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                
                # Create detailed report
                report = f"""
QUALIFIED RFP OPPORTUNITY
=========================

BASIC INFORMATION
-----------------
Title: {opp.get('title', 'N/A')}
Agency: {opp.get('fullParentPathName', 'N/A')}
Notice ID: {opp.get('noticeId', 'N/A')}
Solicitation: {opp.get('solicitationNumber', 'N/A')}
Posted: {opp.get('postedDate', 'N/A')}
Response Deadline: {opp.get('responseDeadLine', 'N/A')}

DESCRIPTION
-----------
{opp.get('description', 'No description available')}

AI ASSESSMENT (Score: {assessment.get('relevance_score', 0)}/10)
--------------------------------------------------------------
WHY THIS IS A FIT:
{assessment.get('justification', 'N/A')}

HOW AI/ML APPLIES:
{assessment.get('ai_application', 'N/A')}

KEY REQUIREMENTS:
{chr(10).join('• ' + req for req in assessment.get('key_requirements', []))}

COMPANY ADVANTAGES:
{chr(10).join('• ' + adv for adv in assessment.get('company_advantages', []))}

SUGGESTED APPROACH:
{assessment.get('suggested_approach', 'N/A')}

LINKS
-----
SAM.gov: {opp.get('uiLink', 'N/A')}
"""
                
                # Upload report
                drive_manager.upload_file(
                    report.encode('utf-8'),
                    'opportunity_analysis.txt',
                    folder_id,
                    'text/plain'
                )
                
                url = drive_manager.get_folder_url(folder_id)
                print(f"✓ {opp.get('title', '')[:50]}...")
                print(f"  Folder: {url}\n")
                
            except Exception as e:
                print(f"⚠️ Error storing: {str(e)[:50]}\n")
    
    print("=" * 70)
    print("\n✨ DISCOVERY COMPLETE!\n")
    
    if qualified:
        print("Top qualified opportunities have been stored in your Google Drive.")
        print(f"Drive folder: https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
    else:
        print("No qualified opportunities found in this search.")
        print("This could be normal - AI-specific RFPs aren't posted every day.")
    
    print("\nTo track these in a spreadsheet:")
    print("1. Create a Google Sheet")
    print("2. Share with: rfp-discovery-bot@rfp-discovery-system.iam.gserviceaccount.com")
    print("3. We'll set up automated tracking")

if __name__ == "__main__":
    find_rfps()