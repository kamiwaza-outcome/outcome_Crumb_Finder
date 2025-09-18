#!/usr/bin/env python3
"""
OVERKILL MODE - Process ALL RFPs from specified date
- Fetches all RFPs from the specified date
- Uses 200 concurrent mini screeners and 30 concurrent deep analyzers 
- Includes proper error handling and progress tracking
- Writes results to Google Sheets
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Initialize environment - add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# Import modules from their reorganized locations
from config import Config
from src.sam_client import SAMClient
from src.ai_qualifier import AIQualifier
from src.sheets_manager import SheetsManager
from src.drive_manager import DriveManager
from archive.parallel_processor import ParallelProcessor
from archive.parallel_mini_processor import ParallelMiniProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('overkill_mode.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def search_all_rfps_for_date(sam_client, target_date):
    """
    OVERKILL MODE: Get ALL RFPs for the target date without any filters
    Based on search_overkill function from enhanced_discovery.py
    """
    all_opportunities = []
    offset = 0
    limit = 100
    
    logger.info(f"OVERKILL: Getting ALL RFPs for {target_date}")
    logger.info(f"Starting overkill search for {target_date}")
    
    while True:
        params = {
            'api_key': Config.SAM_API_KEY,
            'postedFrom': target_date,
            'postedTo': target_date,
            'limit': limit,
            'offset': offset,
            'active': 'true'
        }
        
        try:
            response = sam_client._make_request(params)
            if not response:
                break
                
            batch = response.get('opportunitiesData', [])
            if not batch:
                break
                
            all_opportunities.extend(batch)
            logger.info(f"Retrieved {len(batch)} RFPs (total: {len(all_opportunities)})")
            logger.info(f"Batch retrieved: {len(batch)}, Total: {len(all_opportunities)}")
            
            # Check if there are more
            if len(batch) < limit:
                break
                
            offset += limit
            time.sleep(0.2)  # Be nice to the API
            
        except Exception as e:
            logger.error(f"Error during overkill search at offset {offset}: {str(e)}")
            # Don't break on error, just log and continue
            time.sleep(1)  # Wait a bit longer on error
            if len(all_opportunities) == 0:
                # If we haven't gotten any results yet, break
                break
    
    logger.info(f"OVERKILL COMPLETE: {len(all_opportunities)} total RFPs found")
    logger.info(f"Overkill search complete: {len(all_opportunities)} RFPs found")
    return all_opportunities

def setup_sheets(sheets_manager):
    """Setup headers for all sheets (same pattern as enhanced_discovery.py)"""
    
    # Setup spam sheet (all RFPs)
    if Config.SPAM_SPREADSHEET_ID:
        try:
            sheets_manager.setup_spam_sheet_headers(Config.SPAM_SPREADSHEET_ID)
            logger.info("Spam sheet headers setup complete")
        except Exception as e:
            logger.warning(f"Could not setup spam sheet headers: {e}")
    
    # Setup maybe sheet
    if Config.MAYBE_SPREADSHEET_ID:
        try:
            # Check if headers exist
            result = sheets_manager.service.spreadsheets().values().get(
                spreadsheetId=Config.MAYBE_SPREADSHEET_ID,
                range='A1:N1'
            ).execute()
            
            if not result.get('values'):
                # Add headers for maybe sheet
                headers = [[
                    'AI Score',
                    'Title',
                    'Agency',
                    'Type', 
                    'NAICS',
                    'Posted',
                    'Deadline',
                    'Uncertainty Factors',
                    'AI Justification',
                    'Potential AI Application',
                    'SAM Link',
                    'Notice ID',
                    'Evaluated'
                ]]
                
                sheets_manager.service.spreadsheets().values().update(
                    spreadsheetId=Config.MAYBE_SPREADSHEET_ID,
                    range='A1:M1',
                    valueInputOption='USER_ENTERED',
                    body={'values': headers}
                ).execute()
                
                logger.info("Set up maybe sheet headers")
        except Exception as e:
            logger.warning(f"Could not setup maybe sheet headers: {e}")

def overkill_processor(target_date=None, max_rfps=None):
    """
    Main overkill processing function

    Args:
        target_date: Date to process (MM/DD/YYYY format)
        max_rfps: Maximum RFPs to process (None = no limit)
    """

    # Handle default date if not provided
    if target_date is None:
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime('%m/%d/%Y')

    print("\n" + "="*70)
    logger.info("🔥 OVERKILL MODE - PROCESSING ALL RFPS FROM SPECIFIED DATE")
    print("🔥 OVERKILL MODE - PROCESSING ALL RFPS FROM SPECIFIED DATE")
    print("="*70)
    print(f"📊 Target Date: {target_date}")
    print(f"📊 Qualified Sheet: .../{Config.SPREADSHEET_ID[-6:] if Config.SPREADSHEET_ID else 'NOT_SET'}")
    print(f"🤔 Maybe Sheet: .../{Config.MAYBE_SPREADSHEET_ID[-6:] if Config.MAYBE_SPREADSHEET_ID else 'NOT_SET'}")
    print(f"📋 All RFPs Sheet: .../{Config.SPAM_SPREADSHEET_ID[-6:] if Config.SPAM_SPREADSHEET_ID else 'NOT_SET'}")
    print("="*70)
    
    # Initialize result collections
    all_results = []
    qualified = []
    maybe = []
    rejected = []
    to_process = []
    
    # Initialize services (same pattern as enhanced_discovery.py)
    try:
        logger.info("Initializing services...")
        print("\n🔧 Initializing services...")
        sam_client = SAMClient(Config.SAM_API_KEY)
        qualifier = AIQualifier(Config.OPENAI_API_KEY)
        sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
        drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
        
        # Setup all sheets
        setup_sheets(sheets_manager)
        logger.info("Services initialized successfully")
        print("✅ Services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        logger.error(f"Service initialization failed: {e}")
        print(f"❌ Service initialization failed: {e}")
        return
    
    try:
        # ========== FETCH ALL RFPS ==========
        logger.info(f"Fetching ALL RFPs for {target_date}")
        print(f"\n🔍 Fetching ALL RFPs for {target_date}...")
        
        all_opportunities = search_all_rfps_for_date(sam_client, target_date)
        
        if not all_opportunities:
            logger.warning("No RFPs found for the target date")
            print("❌ No RFPs found for the target date")
            logger.warning(f"No RFPs found for {target_date}")
            return
        
        logger.info(f"Found {len(all_opportunities)} total RFPs for {target_date}")
        print(f"📊 Found {len(all_opportunities)} total RFPs for {target_date}")
        
        # Apply max limit if specified
        if max_rfps and len(all_opportunities) > max_rfps:
            logger.info(f"Limiting to {max_rfps} RFPs (found {len(all_opportunities)})")
            print(f"⚠️ Limiting to {max_rfps} RFPs (found {len(all_opportunities)})")
            to_process = all_opportunities[:max_rfps]
        else:
            to_process = all_opportunities
        
        logger.info(f"Processing {len(to_process)} RFPs")
        print(f"📊 Processing {len(to_process)} RFPs")
        
        # Get existing Notice IDs for duplicate detection
        logger.info("Loading existing Notice IDs for duplicate detection")
        print("\n🔍 Loading existing Notice IDs for duplicate detection...")
        existing_main_ids = sheets_manager.get_existing_notice_ids(Config.SPREADSHEET_ID) if Config.SPREADSHEET_ID else set()
        existing_maybe_ids = sheets_manager.get_existing_notice_ids(Config.MAYBE_SPREADSHEET_ID) if Config.MAYBE_SPREADSHEET_ID else set()
        existing_spam_ids = sheets_manager.get_existing_notice_ids(Config.SPAM_SPREADSHEET_ID) if Config.SPAM_SPREADSHEET_ID else set()

        all_existing_ids = existing_main_ids | existing_maybe_ids | existing_spam_ids
        logger.info(f"Found {len(all_existing_ids)} existing RFPs across all sheets")
        print(f"  Found {len(all_existing_ids)} existing RFPs across all sheets")

        # Pre-LLM duplicate check
        logger.info("Checking for duplicates before AI evaluation")
        print("\n🔎 Checking for duplicates before AI evaluation...")
        duplicates_skipped = 0
        to_process_deduped = []

        for opp in to_process:
            notice_id = opp.get('noticeId', '')
            if notice_id and notice_id in all_existing_ids:
                duplicates_skipped += 1
                logger.info(f"Skipping duplicate Notice ID: {notice_id}")
            else:
                to_process_deduped.append(opp)

        if duplicates_skipped > 0:
            logger.info(f"Skipped {duplicates_skipped} duplicates already in sheets")
            print(f"  ⚠️ Skipped {duplicates_skipped} duplicates already in sheets")

        to_process = to_process_deduped
        print(f"📊 {len(to_process)} RFPs remaining after duplicate removal")

        if not to_process:
            print("ℹ️ No new RFPs to process after duplicate removal")
            return
        
        # ========== PHASE 1: GPT-5-MINI RAPID SCREENING ==========
        print(f"\n⚡ PHASE 1: Rapid screening {len(to_process)} RFPs with GPT-5-mini (200 concurrent)...")
        print("="*70)
        
        # Initialize mini processor with ultra high concurrency
        mini_processor = ParallelMiniProcessor(Config.OPENAI_API_KEY, max_concurrent=200)
        
        # Quick screen all RFPs
        candidates_for_deep, maybe_from_mini, rejected_by_mini = mini_processor.process_batch(
            to_process, 
            threshold=4  # Use threshold of 4
        )
        
        print(f"\n📊 Mini screening results:")
        print(f"  ✅ {len([c for c in candidates_for_deep if c.get('mini_screen', {}).get('score', 0) >= 7])} high-priority (7-10)")
        print(f"  🤔 {len(maybe_from_mini)} maybe (4-6)")
        print(f"  ❌ {len(rejected_by_mini)} rejected (1-3)")
        print(f"  📋 Total for deep analysis: {len(candidates_for_deep)}")
        
        # ========== PHASE 2: GPT-5 DEEP ANALYSIS ==========
        print(f"\n🔬 PHASE 2: Deep analysis of {len(candidates_for_deep)} promising RFPs with GPT-5 (30 concurrent)...")
        print("="*70)
        
        # Initialize parallel processor with 30 concurrent workers
        parallel_processor = ParallelProcessor(qualifier, max_concurrent=30)
        
        # Deep analysis only on candidates that passed mini screening
        if candidates_for_deep:
            deep_results = parallel_processor.process_batch(candidates_for_deep, start_index=1)
        else:
            deep_results = []
            print("  No candidates passed mini screening for deep analysis")
        
        # Combine results: deep analysis results + rejected by mini (with mini scores)
        all_results = deep_results
        
        # Add rejected items to all_results with mini screening scores
        for rejected_item in rejected_by_mini:
            mini_score = rejected_item.get('mini_screen', {}).get('score', 0)
            mini_reason = rejected_item.get('mini_screen', {}).get('reason', 'Rejected by mini screener')
            
            all_results.append({
                'opportunity': rejected_item,
                'assessment': {
                    'is_qualified': False,
                    'relevance_score': mini_score,
                    'justification': f"Mini screening: {mini_reason}",
                    'key_requirements': [],
                    'company_advantages': [],
                    'suggested_approach': '',
                    'ai_application': '',
                    'screener': 'gpt-5-mini'
                }
            })
        
        # Sort results into tiers based on scores
        qualified = []  # 7-10 from deep analysis
        maybe = []      # 4-6 from deep analysis  
        rejected = []   # 1-3 from either screening
        
        for result in all_results:
            score = result['assessment'].get('relevance_score', 0)
            screener = result['assessment'].get('screener', 'gpt-5')
            
            # Only count as qualified/maybe if from deep analysis
            if screener != 'gpt-5-mini' and score >= 7:
                qualified.append(result)
            elif screener != 'gpt-5-mini' and score >= 4:
                maybe.append(result)
            else:
                rejected.append(result)
        
        print("\n" + "="*70)
        print("📊 OVERKILL PROCESSING COMPLETE")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user - saving partial results...")
        logger.info("Process interrupted - will save partial results")
    except Exception as e:
        print(f"\n\n❌ Error during processing: {str(e)}")
        logger.error(f"Processing error: {str(e)}", exc_info=True)
    finally:
        # ========== ALWAYS WRITE RESULTS TO SHEETS ==========
        print("\n📝 Writing results to Google Sheets...")
        
        # Write ALL RFPs to spam sheet
        if all_results and Config.SPAM_SPREADSHEET_ID:
            print(f"\n📋 Writing {len(all_results)} RFPs to all RFPs sheet...")
            
            spam_rows = []
            for item in all_results:
                opp = item['opportunity']
                assessment = item['assessment']
                
                screener = assessment.get('screener', 'gpt-5')
                score_prefix = f"[{screener}] " if screener == 'gpt-5-mini' else ""
                
                spam_rows.append([
                    score_prefix + str(assessment.get('relevance_score', 0)),
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
                    f'=HYPERLINK("{opp.get("uiLink", "")}", "{opp.get("uiLink", "")}")',
                    opp.get('noticeId', ''),
                    datetime.now().strftime('%Y-%m-%d %H:%M')
                ])
            
            # Write in batches to avoid timeout
            batch_size = 500
            total_written = 0

            for i in range(0, len(spam_rows), batch_size):
                batch = spam_rows[i:i+batch_size]
                try:
                    sheets_manager.service.spreadsheets().values().append(
                        spreadsheetId=Config.SPAM_SPREADSHEET_ID,
                        range='A:N',
                        valueInputOption='USER_ENTERED',
                        insertDataOption='INSERT_ROWS',
                        body={'values': batch}
                    ).execute()
                    total_written += len(batch)
                    print(f"    • Batch {i//batch_size + 1}: Added {len(batch)} RFPs ({total_written}/{len(spam_rows)} total)")
                    time.sleep(0.5)  # Small delay between batches to avoid rate limits
                except Exception as e:
                    logger.error(f"Error writing batch {i//batch_size + 1} to spam sheet: {str(e)}")

            if total_written > 0:
                print(f"  ✓ Added {total_written} RFPs to all RFPs sheet")
            else:
                print(f"  ❌ Failed to write RFPs to spam sheet")
        
        # Write MAYBE opportunities (4-6)
        if maybe and Config.MAYBE_SPREADSHEET_ID:
            print(f"\n🤔 Writing {len(maybe)} maybe RFPs to review sheet...")
            
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
                    assessment.get('ai_application', '')[:300] if assessment.get('ai_application') else 'Potential application unclear',
                    f'=HYPERLINK("{opp.get("uiLink", "")}", "{opp.get("uiLink", "")}")',
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
                print(f"  ✓ Added {len(maybe_rows)} to maybe sheet for review")
            except Exception as e:
                logger.error(f"Error writing to maybe sheet: {str(e)}")
        
        # Process QUALIFIED opportunities (7-10)
        if qualified and Config.SPREADSHEET_ID and Config.GOOGLE_DRIVE_FOLDER_ID:
            print(f"\n✅ Processing {len(qualified)} qualified RFPs...")
            
            for item in qualified:
                opp = item['opportunity']
                assessment = item['assessment']
                notice_id = opp.get('noticeId', '')
                
                try:
                    # Create Drive folder
                    folder_name = f"{notice_id[:20]} - {opp.get('title', '')[:30]}"
                    # Create folder in RFP_Files subfolder instead of main folder
                    folder_id = drive_manager.create_folder(folder_name, Config.DAILY_RFPS_FOLDER_ID)
                    
                    # Download and store RFP attachments (up to 50 now)
                    print(f"  📎 Processing {opp.get('title', '')[:40]}...")
                    # Get attachments from the opportunity
                    attachments = opp.get('resourceLinks', [])
                    # Ensure attachments is a list and convert strings to proper format
                    if isinstance(attachments, str):
                        # Single URL string - convert to dict format expected by drive_manager
                        attachments = [{'url': attachments, 'name': 'attachment'}] if attachments else []
                    elif isinstance(attachments, list):
                        # Handle list that might contain strings or dicts
                        formatted_attachments = []
                        for attachment in attachments:
                            if isinstance(attachment, str):
                                formatted_attachments.append({'url': attachment, 'name': 'attachment'})
                            elif isinstance(attachment, dict) and attachment.get('url'):
                                formatted_attachments.append(attachment)
                        attachments = formatted_attachments
                    else:
                        attachments = []

                    if attachments:
                        try:
                            # Pass SAM API key for authentication
                            stored_files = drive_manager.process_rfp_attachments(attachments, folder_id, api_key=Config.SAM_API_KEY)
                            if stored_files:
                                print(f"     Stored {len(stored_files)} attachments")
                        except Exception as e:
                            logger.warning(f"     Could not process attachments: {str(e)}")
                            print(f"     Warning: Could not process attachments")
                    else:
                        print(f"     No attachments found")
                    
                    # Create comprehensive info document with ALL RFP data
                    print(f"     Creating comprehensive info document...")
                    info_doc_link = drive_manager.create_info_document(opp, folder_id)
                    if info_doc_link:
                        print(f"     ✓ Created full info document")
                    
                    # Create detailed assessment document
                    doc_content = f"""QUALIFIED RFP - Score: {assessment.get('relevance_score')}/10

{opp.get('title')}
{opp.get('fullParentPathName')}
Posted: {opp.get('postedDate')}
Deadline: {opp.get('responseDeadLine')}
NAICS: {opp.get('naicsCode')}

FULL DESCRIPTION:
{opp.get('description', 'N/A')}

AI ASSESSMENT:
{assessment.get('justification')}

HOW {Config.get_company_name()} APPLIES:
{assessment.get('ai_application')}

SIMILAR PAST WINS:
{', '.join(assessment.get('similar_past_rfps', [])) or 'None directly identified'}

KEY REQUIREMENTS:
{chr(10).join('• ' + req for req in assessment.get('key_requirements', []))}

COMPANY ADVANTAGES:
{chr(10).join('• ' + adv for adv in assessment.get('company_advantages', []))}

SUGGESTED APPROACH:
{assessment.get('suggested_approach')}

SAM.gov: {opp.get('uiLink')}
"""
                    
                    drive_manager.upload_file(
                        doc_content.encode('utf-8'),
                        'assessment.txt',
                        folder_id,
                        'text/plain'
                    )
                    
                    folder_url = drive_manager.get_folder_url(folder_id)
                    
                    # Add to main sheet with info doc link
                    sheets_manager.add_opportunity(
                        Config.SPREADSHEET_ID,
                        opp,
                        assessment,
                        folder_url,
                        info_doc_link
                    )
                    
                    print(f"  ✓ {opp.get('title', '')[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error processing qualified: {str(e)}")
        
        # Final summary
        print("\n" + "="*70)
        print("📊 OVERKILL MODE SUMMARY")
        print("="*70)
        print(f"🔥 Target Date: {target_date}")
        print(f"📊 Total RFPs Found: {len(all_opportunities) if 'all_opportunities' in locals() else 0}")
        print(f"📊 RFPs Processed: {len(to_process) if 'to_process' in locals() else 0}")
        
        if all_results:
            print(f"\n⚡ Phase 1 - GPT-5-mini Screening:")
            print(f"  • Total Screened: {len(to_process)}")
            print(f"  • Passed to Phase 2: {len(candidates_for_deep) if 'candidates_for_deep' in locals() else 0}")
            print(f"  • Rejected Early: {len(rejected_by_mini) if 'rejected_by_mini' in locals() else 0}")
            
            print(f"\n🔬 Phase 2 - GPT-5 Deep Analysis:")
            print(f"  • Deep Analyzed: {len(candidates_for_deep) if 'candidates_for_deep' in locals() else 0}")
            print(f"  • Qualified (7-10): {len(qualified)} → Main sheet + Drive")
            print(f"  • Maybe (4-6): {len(maybe)} → Review sheet")
            print(f"  • Total Rejected: {len(rejected)} → All RFPs sheet")
            
            avg = sum(r['assessment'].get('relevance_score', 0) for r in all_results) / len(all_results)
            print(f"\n  • Average Score: {avg:.1f}/10")
        
        print(f"\n📂 View Results:")
        if Config.SPREADSHEET_ID:
            print(f"  • Qualified (7-10): https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
        if Config.MAYBE_SPREADSHEET_ID:
            print(f"  • Maybe (4-6): https://docs.google.com/spreadsheets/d/{Config.MAYBE_SPREADSHEET_ID}")
        if Config.SPAM_SPREADSHEET_ID:
            print(f"  • All RFPs: https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
        if Config.GOOGLE_DRIVE_FOLDER_ID and qualified:
            print(f"  • Documents: https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
        
        print("\n✨ Overkill mode complete!\n")
        
        # Cleanup
        try:
            sam_client.close()
        except:
            pass
        
        return {
            'qualified': qualified,
            'maybe': maybe, 
            'rejected': rejected,
            'total': len(all_results) if all_results else 0
        }

def test_connection():
    """Test that the system can connect and fetch RFPs"""
    print("\n🧪 TESTING CONNECTION...")
    
    try:
        # Test SAM client
        sam_client = SAMClient(Config.SAM_API_KEY)
        
        # Try to get just one page of RFPs
        params = {
            'api_key': Config.SAM_API_KEY,
            'postedFrom': target_date,
            'postedTo': target_date, 
            'limit': 10,
            'offset': 0,
            'active': 'true'
        }
        
        print("  Testing SAM API connection...")
        response = sam_client._make_request(params)
        
        if response and 'opportunitiesData' in response:
            rfps = response.get('opportunitiesData', [])
            total_records = response.get('totalRecords', 0)
            print(f"  ✅ Connection successful!")
            print(f"  📊 Found {total_records} total RFPs for {target_date}")
            print(f"  📝 Sample: {len(rfps)} RFPs in test batch")
            
            if rfps:
                sample = rfps[0]
                print(f"  📌 First RFP: {sample.get('title', 'No title')[:60]}...")
            
            sam_client.close()
            return True
        else:
            print("  ❌ No data received from SAM API")
            return False
            
    except Exception as e:
        print(f"  ❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Overkill Mode RFP Processor')
    parser.add_argument('--test', action='store_true', help='Test connection only')
    parser.add_argument('--date', type=str, default=None, help='Target date (MM/DD/YYYY, defaults to yesterday)')
    parser.add_argument('--max', type=int, help='Maximum RFPs to process')
    
    args = parser.parse_args()
    
    if args.test:
        success = test_connection()
        sys.exit(0 if success else 1)
    else:
        result = overkill_processor(target_date=args.date, max_rfps=args.max)
        if result:
            print(f"\n🎯 Final Results: {result['qualified']} qualified, {result['maybe']} maybe, {result['rejected']} rejected")