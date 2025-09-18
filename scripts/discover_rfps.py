#!/usr/bin/env python3
"""
Production RFP Discovery Script
- Searches for yesterday's RFPs (or today's for testing)
- Logs ALL to spam sheet with scores
- Adds qualified (7+/10) to main sheet
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

def discover_rfps(test_mode=False, max_rfps=50):
    print("\n" + "="*70)
    print("🚀 RFP DISCOVERY SYSTEM")
    print("="*70)
    print(f"📊 Main Sheet: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    print(f"📋 Spam Sheet: https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    print("="*70)
    
    # Initialize
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Setup spam sheet headers if needed
    sheets_manager.setup_spam_sheet_headers(Config.SPAM_SPREADSHEET_ID)
    
    # Date range
    if test_mode:
        # For testing, use today
        target_date = datetime.now().strftime('%m/%d/%Y')
        print(f"\n🧪 TEST MODE - Searching today's RFPs: {target_date}")
    else:
        # Production: yesterday's RFPs
        target_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
        print(f"\n📅 Searching yesterday's RFPs: {target_date}")
    
    # Keywords to search
    keywords = [
        'artificial intelligence',
        'machine learning',
        'data analytics',
        'data processing',
        'predictive analytics',
        'automation',
        'software development'
    ]
    
    # NAICS codes for IT services
    naics_codes = ['541511', '541512', '518210']
    
    print("\n🔍 Searching SAM.gov...")
    all_opportunities = []
    
    # Search by keywords (limited per keyword)
    for keyword in keywords[:5]:  # Limit keywords
        params = {
            'q': keyword,
            'postedFrom': target_date,
            'postedTo': target_date,
            'limit': 5,  # Small limit per keyword
            'offset': 0,
            'ptype': 'o,p,r,g',
            'api_key': sam_client.api_key
        }
        
        try:
            data = sam_client._make_request(params)
            opps = data.get('opportunitiesData', [])
            
            # Filter for exact date match
            target_ymd = datetime.strptime(target_date, '%m/%d/%Y').strftime('%Y-%m-%d')
            for opp in opps:
                if opp.get('postedDate') == target_ymd:
                    all_opportunities.append(opp)
                    
        except Exception as e:
            print(f"  Warning: {keyword} - {str(e)[:30]}")
        
        time.sleep(0.2)  # Rate limiting
    
    # Search by NAICS
    for naics in naics_codes:
        params = {
            'ncode': naics,
            'postedFrom': target_date,
            'postedTo': target_date,
            'limit': 3,
            'offset': 0,
            'ptype': 'o,p,r,g',
            'api_key': sam_client.api_key
        }
        
        try:
            data = sam_client._make_request(params)
            opps = data.get('opportunitiesData', [])
            
            target_ymd = datetime.strptime(target_date, '%m/%d/%Y').strftime('%Y-%m-%d')
            for opp in opps:
                if opp.get('postedDate') == target_ymd:
                    all_opportunities.append(opp)
                    
        except Exception as e:
            print(f"  Warning: NAICS {naics} - {str(e)[:30]}")
        
        time.sleep(0.2)
    
    # Deduplicate
    unique = {}
    for opp in all_opportunities:
        notice_id = opp.get('noticeId')
        if notice_id and notice_id not in unique:
            unique[notice_id] = opp
    
    # Limit total
    to_process = list(unique.values())[:max_rfps]
    
    print(f"  Found {len(to_process)} unique RFPs to evaluate")
    print("\n" + "="*70)
    print(f"\n🤖 EVALUATING {len(to_process)} RFPs WITH AI...\n")
    
    # Process all RFPs
    all_assessments = []
    qualified = []
    
    for i, opp in enumerate(to_process, 1):
        title = opp.get('title', 'Unknown')[:60]
        print(f"{i:3}. {title}...", end="")
        
        try:
            # AI evaluation
            assessment = qualifier.assess_opportunity(opp)
            score = assessment.get('relevance_score', 0)
            
            print(f" [{score}/10]", end="")
            
            # Store for batch operations
            all_assessments.append({
                'opportunity': opp,
                'assessment': assessment
            })
            
            if assessment.get('is_qualified'):
                print(" ✅")
                qualified.append({
                    'opportunity': opp,
                    'assessment': assessment
                })
            else:
                print("")
            
            # Rate limiting
            if i % 10 == 0:
                time.sleep(1)
            
        except Exception as e:
            print(f" ⚠️ {str(e)[:30]}")
    
    print("\n" + "="*70)
    
    # BATCH write ALL to spam sheet
    if all_assessments:
        print(f"\n📋 Writing {len(all_assessments)} RFPs to spam sheet...")
        
        spam_rows = []
        for item in all_assessments:
            opp = item['opportunity']
            assessment = item['assessment']
            
            spam_rows.append([
                str(assessment.get('relevance_score', 0)),
                '✅' if assessment.get('is_qualified', False) else '❌',
                opp.get('title', '')[:200],
                opp.get('fullParentPathName', '')[:100],
                opp.get('type', ''),
                opp.get('naicsCode', ''),
                opp.get('postedDate', ''),
                opp.get('responseDeadLine', ''),
                assessment.get('justification', '')[:300],
                assessment.get('ai_application', '')[:200] if assessment.get('ai_application') else '',
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
            print(f"  ✓ Added all {len(spam_rows)} RFPs to spam sheet")
        except Exception as e:
            print(f"  ⚠️ Error writing to spam sheet: {str(e)[:50]}")
    
    # Add qualified to main sheet
    if qualified:
        print(f"\n🎯 Processing {len(qualified)} qualified RFPs for main sheet...")
        
        for item in qualified[:5]:  # Limit to top 5 for main sheet
            opp = item['opportunity']
            assessment = item['assessment']
            
            try:
                # Create Drive folder
                folder_name = f"{opp.get('noticeId', '')[:20]} - {opp.get('title', '')[:30]}"
                folder_id = drive_manager.create_folder(folder_name, Config.GOOGLE_DRIVE_FOLDER_ID)
                
                # Quick assessment doc
                doc_content = f"""QUALIFIED RFP - Score: {assessment.get('relevance_score')}/10

{opp.get('title')}
{opp.get('fullParentPathName')}
Deadline: {opp.get('responseDeadLine')}

WHY QUALIFIED:
{assessment.get('justification')}

AI APPLICATION:
{assessment.get('ai_application')}

SIMILAR PAST WINS:
{', '.join(assessment.get('similar_past_rfps', [])) or 'None identified'}
"""
                drive_manager.upload_file(
                    doc_content.encode('utf-8'),
                    'assessment.txt',
                    folder_id,
                    'text/plain'
                )
                
                folder_url = drive_manager.get_folder_url(folder_id)
                
                # Add to main sheet
                sheets_manager.add_opportunity(
                    Config.SPREADSHEET_ID,
                    opp,
                    assessment,
                    folder_url
                )
                
                print(f"  ✓ {opp.get('title', '')[:50]}...")
                
            except Exception as e:
                print(f"  ⚠️ Error: {str(e)[:50]}")
    
    # Summary
    print("\n" + "="*70)
    print("\n📊 DISCOVERY COMPLETE!\n")
    print(f"  • Total Evaluated: {len(all_assessments)}")
    print(f"  • Qualified (7+/10): {len(qualified)}")
    
    if all_assessments:
        avg = sum(a['assessment'].get('relevance_score', 0) for a in all_assessments) / len(all_assessments)
        print(f"  • Average Score: {avg:.1f}/10")
    
    print(f"\n📋 View ALL RFPs with scores:")
    print(f"  https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    
    print(f"\n🎯 View QUALIFIED RFPs only:")
    print(f"  https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    
    print("\n✨ Done! Check your sheets for results.\n")
    
    return qualified

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='RFP Discovery System')
    parser.add_argument('--test', action='store_true', help='Test mode (search today)')
    parser.add_argument('--max', type=int, default=50, help='Max RFPs to process')
    
    args = parser.parse_args()
    
    discover_rfps(test_mode=args.test, max_rfps=args.max)