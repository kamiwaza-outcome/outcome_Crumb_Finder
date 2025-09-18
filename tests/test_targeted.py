#!/usr/bin/env python3
"""
Targeted test for AI-specific RFPs that match the company's capabilities
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

def test_targeted_rfps():
    print("\n🎯 COMPANY RFP DISCOVERY - TARGETED AI SEARCH\n")
    print("=" * 70)
    
    # Initialize clients
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Search last 30 days for more results
    search_from = (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y')
    search_to = datetime.now().strftime('%m/%d/%Y')
    
    print(f"📅 Searching: {search_from} to {search_to}\n")
    
    # More targeted keywords based on the company's capabilities
    targeted_keywords = [
        'data processing',
        'predictive analytics',
        'document processing',
        'natural language processing',
        'computer vision',
        'data migration',
        'data integration',
        'AI platform'
    ]
    
    # Also search with NAICS codes for IT services
    naics_codes = [
        '541511',  # Custom Computer Programming Services
        '541512',  # Computer Systems Design Services
        '518210',  # Data Processing, Hosting, and Related Services
    ]
    
    all_opportunities = []
    
    print("🔍 Searching for AI/Data opportunities...\n")
    
    # Search by keywords
    print("Keywords search:")
    for keyword in targeted_keywords[:4]:  # Limit to 4 keywords
        print(f"  {keyword}...", end=" ")
        try:
            opps = sam_client.search_by_keyword(keyword, search_from, search_to)
            print(f"Found {len(opps)}")
            all_opportunities.extend(opps[:10])  # Take first 10 from each
        except Exception as e:
            print(f"Error: {str(e)[:30]}")
    
    # Search by NAICS codes
    print("\nNAICS codes search:")
    for naics in naics_codes:
        print(f"  {naics}...", end=" ")
        try:
            opps = sam_client.search_by_naics(naics, search_from, search_to)
            print(f"Found {len(opps)}")
            all_opportunities.extend(opps[:5])  # Take first 5 from each
        except Exception as e:
            print(f"Error: {str(e)[:30]}")
    
    # Deduplicate
    unique = {}
    for opp in all_opportunities:
        notice_id = opp.get('noticeId')
        if notice_id and notice_id not in unique:
            # Filter for more relevant opportunities
            title = opp.get('title', '').lower()
            desc = opp.get('description', '').lower()
            
            # Check if it contains AI-relevant terms
            ai_terms = ['data', 'analytic', 'software', 'system', 'automat', 
                       'process', 'integrat', 'transform', 'modern', 'cloud',
                       'intelligence', 'learning', 'predict', 'decision']
            
            if any(term in title or term in desc for term in ai_terms):
                unique[notice_id] = opp
    
    print(f"\n📊 Found {len(unique)} potentially relevant opportunities\n")
    print("=" * 70)
    
    # Process only first 8 for testing
    test_batch = list(unique.items())[:8]
    
    # Evaluate with AI
    print("\n🤖 EVALUATING WITH COMPANY'S AI CRITERIA...\n")
    
    qualified = []
    for i, (notice_id, opp) in enumerate(test_batch, 1):
        title = opp.get('title', 'Unknown')[:70]
        print(f"{i}. {title}...")
        print(f"   Agency: {opp.get('fullParentPathName', 'Unknown')[:50]}")
        
        # Show a bit of description to understand what it's about
        desc_preview = opp.get('description', '')[:150].replace('\n', ' ')
        if desc_preview:
            print(f"   Preview: {desc_preview}...")
        
        try:
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            print(f"   AI Score: {score}/10", end=" - ")
            
            if assessment.get('is_qualified'):
                print("✅ QUALIFIED FOR COMPANY")
                print(f"   Match: {assessment.get('justification', '')[:200]}...")
                if assessment.get('similar_past_rfps'):
                    print(f"   Similar to: {', '.join(assessment.get('similar_past_rfps', []))}")
                
                qualified.append({
                    'opportunity': opp,
                    'assessment': assessment
                })
            else:
                print("❌ Not optimal fit")
                
        except Exception as e:
            print(f"   ⚠️ Error: {str(e)[:50]}")
        
        print()  # Blank line between opportunities
    
    print("=" * 70)
    print(f"\n🎯 RESULTS: Found {len(qualified)} opportunities matching the company's capabilities\n")
    
    # Store qualified opportunities
    if qualified:
        print("📁 Storing qualified opportunities...\n")
        
        for item in qualified[:3]:  # Store top 3
            opp = item['opportunity']
            assessment = item['assessment']
            
            try:
                print(f"Processing: {opp.get('title', '')[:50]}...")
                
                # Create folder
                folder_name = f"{opp.get('noticeId', 'Unknown')[:20]} - {opp.get('title', 'Unknown')[:30]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                
                # Create assessment report
                report = f"""COMPANY OPPORTUNITY ASSESSMENT
{'='*50}

OPPORTUNITY DETAILS
-------------------
Title: {opp.get('title', 'N/A')}
Agency: {opp.get('fullParentPathName', 'N/A')}
Notice ID: {opp.get('noticeId', 'N/A')}
Solicitation: {opp.get('solicitationNumber', 'N/A')}
Posted: {opp.get('postedDate', 'N/A')}
Response Deadline: {opp.get('responseDeadLine', 'N/A')}
NAICS: {opp.get('naicsCode', 'N/A')}
Type: {opp.get('type', 'N/A')}

DESCRIPTION
-----------
{opp.get('description', 'No description available')[:1500]}

AI ASSESSMENT
--------------
Score: {assessment.get('relevance_score', 0)}/10

WHY THIS IS A GOOD FIT:
{assessment.get('justification', 'N/A')}

HOW THE COMPANY'S PLATFORM APPLIES:
{assessment.get('ai_application', 'N/A')}

SIMILAR PAST WINS:
{', '.join(assessment.get('similar_past_rfps', [])) or 'No direct matches identified'}

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
                    'company_assessment.txt',
                    folder_id,
                    'text/plain'
                )
                
                folder_url = drive_manager.get_folder_url(folder_id)
                print(f"   ✓ Stored in Drive: {folder_url}")
                
                # Add to spreadsheet
                if Config.SPREADSHEET_ID:
                    try:
                        sheets_manager.add_opportunity(
                            Config.SPREADSHEET_ID,
                            opp,
                            assessment,
                            folder_url
                        )
                        print(f"   ✓ Added to tracking spreadsheet")
                        time.sleep(1)  # Avoid rate limits
                    except Exception as e:
                        print(f"   ⚠️ Spreadsheet error: {str(e)[:50]}")
                
            except Exception as e:
                print(f"   ⚠️ Storage error: {str(e)[:100]}")
            
            print()
        
        print("📊 SUMMARY:")
        print(f"   • Evaluated {len(test_batch)} opportunities")
        print(f"   • Found {len(qualified)} qualified matches")
        print(f"   • Stored top {min(3, len(qualified))} in Google Drive")
        
        print(f"\n📂 View in Google Drive:")
        print(f"   https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
        
        if Config.SPREADSHEET_ID:
            print(f"\n📊 Track in spreadsheet:")
            print(f"   https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    else:
        print("No opportunities matched the company's specific capabilities in this batch.")
        print("\nThis could mean:")
        print("  • The current RFPs are focused on other areas")
        print("  • More specific search terms are needed")
        print("  • The time window should be expanded")
    
    print("\n✨ TARGETED SEARCH COMPLETE!\n")

if __name__ == "__main__":
    test_targeted_rfps()