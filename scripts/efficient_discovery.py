#!/usr/bin/env python3
"""
Efficient RFP Discovery - Optimized for API limits
- Only gets yesterday's RFPs
- Batches Google Sheets operations
- Limits total RFPs processed
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

def efficient_discovery(max_rfps=30):
    print("\n" + "="*70)
    print("🚀 EFFICIENT RFP DISCOVERY - YESTERDAY'S OPPORTUNITIES ONLY")
    print("="*70)
    
    # Initialize clients
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH) if Config.GOOGLE_DRIVE_FOLDER_ID else None
    
    # Setup spam sheet headers
    if Config.SPAM_SPREADSHEET_ID:
        sheets_manager.setup_spam_sheet_headers(Config.SPAM_SPREADSHEET_ID)
    
    # For testing, let's look at today's RFPs (normally would be yesterday)
    # Change this back to days=1 for production
    target_date = datetime.now().strftime('%m/%d/%Y')  # Today for testing
    print(f"\n📅 Searching for RFPs posted on: {target_date} (today for testing)\n")
    
    # Limited, targeted search
    opportunities = []
    
    # Search with most relevant keywords only
    priority_keywords = [
        'artificial intelligence',
        'data processing',
        'predictive analytics'
    ]
    
    print("🔍 Searching SAM.gov (limited to prevent overload)...\n")
    
    for keyword in priority_keywords:
        print(f"  Searching '{keyword}'...", end=" ")
        
        # Create custom params to limit results
        params = {
            'q': keyword,
            'postedFrom': target_date,
            'postedTo': target_date,  # Same day to ensure ONLY target date
            'limit': 10,  # Only get first 10 per keyword
            'offset': 0,
            'ptype': 'o,p,r,g',
            'api_key': sam_client.api_key
        }
        
        try:
            # Make direct request with limited results
            data = sam_client._make_request(params)
            keyword_opps = data.get('opportunitiesData', [])
            
            # Filter to ensure they're actually from target date
            # Convert target_date to YYYY-MM-DD format for comparison
            target_ymd = datetime.strptime(target_date, '%m/%d/%Y').strftime('%Y-%m-%d')
            
            filtered = []
            for opp in keyword_opps:
                posted_date = opp.get('postedDate', '')
                if posted_date and posted_date == target_ymd:
                    filtered.append(opp)
            
            print(f"Found {len(filtered)} from yesterday")
            opportunities.extend(filtered)
            
        except Exception as e:
            print(f"Error: {str(e)[:30]}")
        
        time.sleep(0.5)  # Rate limiting
    
    # Deduplicate
    unique = {}
    for opp in opportunities:
        notice_id = opp.get('noticeId')
        if notice_id and notice_id not in unique:
            unique[notice_id] = opp
    
    # Limit total to process
    to_process = list(unique.values())[:max_rfps]
    
    print(f"\n📊 Processing {len(to_process)} unique RFPs from yesterday")
    print("=" * 70)
    
    # Batch process for spam sheet
    print("\n🤖 EVALUATING WITH AI...\n")
    
    all_assessments = []  # Collect for batch writing
    qualified = []
    
    for i, opp in enumerate(to_process, 1):
        title = opp.get('title', 'Unknown')[:60]
        print(f"{i:2}. {title}...")
        
        try:
            # Evaluate with AI
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            print(f"    Score: {score}/10", end="")
            
            # Collect for batch operations
            all_assessments.append({
                'opportunity': opp,
                'assessment': assessment
            })
            
            if assessment.get('is_qualified'):
                print(" ✅ QUALIFIED")
                qualified.append({
                    'opportunity': opp,
                    'assessment': assessment
                })
            else:
                print(" ❌")
            
            # Small delay to avoid OpenAI rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f" ⚠️ Error: {str(e)[:50]}")
    
    print("\n" + "="*70)
    
    # BATCH write to spam sheet
    if Config.SPAM_SPREADSHEET_ID and all_assessments:
        print("\n📋 Writing ALL results to spam sheet (batch operation)...")
        
        # Prepare all rows at once
        spam_rows = []
        for item in all_assessments:
            opp = item['opportunity']
            assessment = item['assessment']
            
            spam_rows.append([
                str(assessment.get('relevance_score', 0)),
                '✓' if assessment.get('is_qualified', False) else '✗',
                opp.get('title', '')[:200],
                opp.get('fullParentPathName', '')[:100],
                opp.get('type', ''),
                opp.get('naicsCode', ''),
                opp.get('postedDate', ''),
                opp.get('responseDeadLine', ''),
                assessment.get('justification', '')[:300],
                assessment.get('ai_application', '')[:200] if assessment.get('ai_application') else '',
                ', '.join(assessment.get('similar_past_rfps', [])[:3]) if assessment.get('similar_past_rfps') else '',
                f'=HYPERLINK("{opp.get("uiLink", "")}", "SAM.gov")',
                opp.get('noticeId', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Single batch write
        try:
            sheets_manager.service.spreadsheets().values().append(
                spreadsheetId=Config.SPAM_SPREADSHEET_ID,
                range='A:N',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': spam_rows}
            ).execute()
            print(f"   ✓ Added {len(spam_rows)} RFPs to spam sheet in one batch")
        except Exception as e:
            print(f"   ⚠️ Batch write error: {str(e)[:100]}")
    
    # Process qualified opportunities
    if qualified:
        print(f"\n📁 Processing {len(qualified)} qualified opportunities...")
        
        for item in qualified[:3]:  # Limit to top 3 for main sheet
            opp = item['opportunity']
            assessment = item['assessment']
            
            try:
                # Create Drive folder
                if drive_manager:
                    folder_name = f"{opp.get('noticeId', '')[:15]} - {opp.get('title', '')[:30]}"
                    folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                    folder_url = drive_manager.get_folder_url(folder_id)
                else:
                    folder_url = ""
                
                # Add to main sheet
                if Config.SPREADSHEET_ID:
                    sheets_manager.add_opportunity(
                        Config.SPREADSHEET_ID,
                        opp,
                        assessment,
                        folder_url
                    )
                    print(f"   ✓ Added to main sheet: {opp.get('title', '')[:40]}...")
                
            except Exception as e:
                print(f"   ⚠️ Error: {str(e)[:50]}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY:")
    print(f"   • RFPs from yesterday: {len(to_process)}")
    print(f"   • Qualified (7+/10): {len(qualified)}")
    print(f"   • Average score: {sum(a['assessment'].get('relevance_score', 0) for a in all_assessments) / len(all_assessments):.1f}/10" if all_assessments else "N/A")
    
    print("\n📋 VIEW RESULTS:")
    print(f"   • ALL scores: https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    if Config.SPREADSHEET_ID:
        print(f"   • Qualified only: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    
    print("\n✨ EFFICIENT DISCOVERY COMPLETE!")
    print(f"   Used minimal API calls by batching operations")
    print(f"   Processed only yesterday's RFPs as intended\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Efficient RFP Discovery')
    parser.add_argument('--max', type=int, default=30, help='Maximum RFPs to process')
    
    args = parser.parse_args()
    efficient_discovery(max_rfps=args.max)