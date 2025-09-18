#!/usr/bin/env python3
"""
Enhanced RFP Discovery System - Three-Tier Scoring
- Searches broadly (200+ RFPs/day)
- Uses full descriptions for better AI analysis
- Sorts into three sheets: Qualified (7-10), Maybe (4-6), All (1-10)
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import logging

# Add parent directory to path to find config and src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from config import Config
from src.sam_client import SAMClient  
from src.ai_qualifier import AIQualifier
from src.sheets_manager import SheetsManager
from src.drive_manager import DriveManager
from archive.parallel_processor import ParallelProcessor
from archive.parallel_mini_processor import ParallelMiniProcessor
from src.carryover_manager import CarryoverManager
from utilities.weekend_catchup import WeekendCatchupManager
from src.health_monitor import health_monitor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_all_sheets(sheets_manager):
    """Setup headers for all three sheets"""
    
    # Setup spam sheet (all RFPs)
    if Config.SPAM_SPREADSHEET_ID:
        sheets_manager.setup_spam_sheet_headers(Config.SPAM_SPREADSHEET_ID)
    
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
        except:
            pass

def search_overkill(sam_client, target_date):
    """OVERKILL MODE: Get ALL RFPs without any filters"""
    
    all_opportunities = []
    offset = 0
    limit = 100
    
    print(f"  🔥 OVERKILL: Getting ALL RFPs for {target_date}")
    
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
            print(f"    Retrieved {len(batch)} RFPs (total: {len(all_opportunities)})")
            
            # Check if there are more
            if len(batch) < limit:
                break
                
            offset += limit
            time.sleep(0.2)  # Be nice to the API
            
        except Exception as e:
            logger.warning(f"    Error during overkill search: {str(e)}")
            break
    
    print(f"  🔥 OVERKILL COMPLETE: {len(all_opportunities)} total RFPs found")
    return all_opportunities

def search_broadly(sam_client, target_date):
    """Cast a VERY wide net to get 500+ RFPs for GPT-5-mini to screen"""
    
    all_opportunities = []
    
    # IT/Tech NAICS codes - COMPREHENSIVE LIST
    # Primary IT Services
    primary_naics = [
        '541511',  # Custom Computer Programming Services
        '541512',  # Computer Systems Design Services
        '541519',  # Other Computer Related Services
        '518210',  # Data Processing, Hosting, and Related Services
    ]
    
    # Secondary IT/Tech Services
    secondary_naics = [
        '541513',  # Computer Facilities Management Services
        '541611',  # Administrative Management Consulting
        '541618',  # Other Management Consulting Services
        '541690',  # Other Scientific and Technical Consulting
        '541990',  # All Other Professional, Scientific, Technical Services
        '541330',  # Engineering Services
        '541715',  # Research and Development in Physical Sciences
        '541714',  # R&D in Biotechnology (often includes bioinformatics/AI)
        '541720',  # R&D in Social Sciences (often includes data analytics)
    ]
    
    # EXPANDED: Additional Research & Analytics
    expanded_research_naics = [
        '541370',  # Research and Development (general)
        '541380',  # Testing Laboratories (often need data systems)
        '541360',  # Geophysical Surveying (big data processing)
        '519130',  # Internet Publishing and Web Portals
        '541430',  # Graphic Design Services (web/app design)
        '541840',  # Advertising Agencies (digital marketing/analytics)
        '541910',  # Marketing Research (data analytics heavy)
    ]
    
    # EXPANDED: Adjacent Professional Services
    adjacent_naics = [
        '541613',  # Marketing Consulting Services
        '541614',  # Process & Logistics Consulting
        '561311',  # Employment Placement Agencies (IT staffing)
        '611420',  # Computer Training
        '541219',  # Other Accounting Services (reporting systems)
        '541820',  # Public Relations Agencies (social media analytics)
        '561110',  # Office Administrative Services (often need IT)
        '561210',  # Facilities Support Services (includes IT support)
    ]
    
    # Telecommunications and Network (often bundled with IT)
    telecom_naics = [
        '517311',  # Wired Telecommunications Carriers
        '517312',  # Wireless Telecommunications Carriers
        '517919',  # All Other Telecommunications
        '517410',  # Satellite Telecommunications
        '517810',  # Other Information Services
    ]
    
    # Combine all NAICS codes
    naics_codes = primary_naics + secondary_naics + expanded_research_naics + adjacent_naics + telecom_naics
    
    # PSC codes for IT/software - EXPANDED LIST
    # Legacy codes (pre-2020, some agencies still use)
    legacy_psc_codes = [
        'D302',   # IT and Telecom - Systems Development (LEGACY)
        'D307',   # IT and Telecom - IT Strategy and Architecture (LEGACY)
        'D399',   # IT and Telecom - Other IT and Telecommunications
        '7030',   # Software (LEGACY)
        'R425',   # Engineering and Technical Services
    ]
    
    # EXPANDED: Adjacent Professional Services PSCs
    adjacent_psc_codes = [
        'R499',   # Other Professional Services (catch-all)
        'B505',   # Special Studies and Analysis - Not R&D
        'R707',   # IT Strategy and Architecture Support
        'H170',   # IT/Telecom Training Services
        'R423',   # Intelligence Services (often needs data analysis)
        'R406',   # Policy Review/Development Services (often needs data)
        'R408',   # Program Management/Support Services
        'R413',   # Specifications Development
        'R414',   # Systems Engineering Services
        'R497',   # Personal Services Contracts
        'B599',   # Other Special Studies and Analyses
        'L099',   # Other Technical Representative Services
    ]
    
    # Modern D-series service codes (post-2020)
    modern_service_psc = [
        'DA01',   # Business Application/App Development Support Services
        'DA10',   # Business Application/App Development SaaS
        'DB01',   # High Performance Computing (HPC) Support Services
        'DC01',   # Data Center Support Services
        'DD01',   # Service Delivery Support: ITSM, Operations Center, PM
        'DE01',   # End User: Help Desk, Workspace, Productivity Tools
        'DF01',   # IT Management Support Services
        'DG01',   # Network Support Services
        'DH01',   # Platform Support: Database, Mainframe, Middleware
        'DH10',   # Platform Support SaaS
        'DJ01',   # Security and Compliance Support Services
        'DJ10',   # Security and Compliance SaaS
        'DK01',   # Storage Support Services (if exists)
        'DK10',   # Storage SaaS (if exists)
    ]
    
    # Modern 7-series product codes (post-2020)
    modern_product_psc = [
        '7A20',   # Application Development Software (Perpetual License)
        '7A21',   # Business Application Software (Perpetual License)
        '7H20',   # Platform Products: Database, Mainframe, Middleware
        '7J20',   # Security and Compliance Products
        '7K20',   # Storage Products (Hardware and Software)
    ]
    
    # Combine all PSC codes
    psc_codes = legacy_psc_codes + adjacent_psc_codes + modern_service_psc + modern_product_psc
    
    logger.info(f"Searching for RFPs from {target_date}")
    
    # Search by NAICS codes
    for naics in naics_codes:
        try:
            opps = sam_client.search_by_naics(naics, target_date, target_date)
            all_opportunities.extend(opps)
            logger.info(f"  NAICS {naics}: Found {len(opps)}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"  NAICS {naics}: Error - {str(e)[:50]}")
    
    # Search by PSC codes
    for psc in psc_codes:
        try:
            opps = sam_client.search_by_psc(psc, target_date, target_date)
            all_opportunities.extend(opps)
            logger.info(f"  PSC {psc}: Found {len(opps)}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"  PSC {psc}: Error - {str(e)[:50]}")
    
    # MASSIVELY EXPANDED keyword searches - casting VERY wide net for 500+ RFPs
    # Priority 1: AI/ML and Data terms (most relevant)
    priority1_keywords = [
        'artificial intelligence', 'machine learning', 'automation', 'predictive analytics',
        'natural language processing', 'computer vision', 'algorithm', 'deep learning',
        'analytics', 'big data', 'data processing', 'data migration', 'data integration',
        'data quality', 'data management', 'modernization', 'digital transformation',
        'cloud migration', 'cloud computing', 'legacy system'
    ]
    
    # Priority 2: Development and Tech terms (good matches)
    priority2_keywords = [
        'development', 'engineering', 'integration', 'API', 'microservices',
        'DevOps', 'agile', 'dashboard', 'visualization', 'reporting',
        'workflow', 'optimization', 'decision support', 'intelligent', 'platform'
    ]
    
    # EXPANDED: Generic professional/technical terms
    generic_keywords = [
        'support', 'technical', 'consulting', 'professional services',
        'maintenance', 'operations', 'management', 'solution', 'program',
        'contract', 'enterprise', 'federal', 'government', 'contractor',
        'upgrade', 'implementation', 'deployment', 'installation', 'configuration',
        'analysis', 'research', 'study', 'assessment', 'evaluation',
        'network', 'infrastructure', 'security', 'cyber', 'compliance',
        'database', 'application', 'web', 'mobile', 'portal',
        'training', 'documentation', 'planning', 'strategy', 'architecture',
        'testing', 'quality', 'assurance', 'monitoring', 'performance',
        'backup', 'recovery', 'disaster', 'continuity', 'resilience',
        'migration', 'transition', 'transformation', 'consolidation', 'integration',
        'acquisition', 'procurement', 'sourcing', 'vendor', 'supplier'
    ]
    
    # Original broad terms still useful
    broad_keywords = ['software', 'system', 'data', 'technology', 'services',
                     'information', 'digital', 'electronic', 'automated', 'virtual']
    
    # Combine all keywords for searching
    all_keywords = priority1_keywords + priority2_keywords + generic_keywords + broad_keywords
    
    logger.info(f"Searching {len(all_keywords)} keyword terms...")
    
    for keyword in all_keywords:
        try:
            # Use the proper search_by_keyword method which handles pagination
            opps = sam_client.search_by_keyword(keyword, target_date, target_date)
            all_opportunities.extend(opps)
            logger.info(f"  Keyword '{keyword}': Found {len(opps)}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"  Keyword '{keyword}': Error - {str(e)[:50]}")
    
    # Deduplicate with size limit
    unique = {}
    for opp in all_opportunities:
        if len(unique) >= Config.MAX_DEDUP_CACHE_SIZE:
            logger.warning(f"Deduplication limit reached: {Config.MAX_DEDUP_CACHE_SIZE}")
            break
        notice_id = opp.get('noticeId')
        if notice_id and notice_id not in unique:
            unique[notice_id] = opp
    
    return list(unique.values())

def filter_obvious_irrelevant(opportunities):
    """Remove only the VERY MOST obvious non-matches - be very permissive"""
    
    filtered = []
    # REDUCED: Only skip the absolute most obvious non-tech
    skip_keywords = [
        'janitorial', 'custodial', 'lawn', 'mowing', 'landscaping',
        'food service', 'cafeteria', 'laundry', 'uniform rental',
        'pest control', 'trash removal', 'refuse collection',
        'plumbing', 'electrical work', 'hvac repair', 'roofing',
        'painting', 'carpet cleaning', 'window washing'
    ]
    
    for opp in opportunities:
        title = opp.get('title', '').lower()
        
        # Skip ONLY if title contains very obvious non-tech keywords
        # Note: We're NOT skipping "maintenance", "security", "support" etc
        # as these could be IT maintenance, cybersecurity, IT support
        if any(skip in title for skip in skip_keywords):
            logger.debug(f"  Skipping obvious non-match: {title[:50]}")
            continue
            
        # Skip if it's just an award notification
        if opp.get('type') in ['Award', 'Justification']:
            continue
            
        filtered.append(opp)
    
    return filtered

def enhanced_discovery(test_mode=False, max_rfps=500, overkill_mode=False, days_back=1):
    """Main discovery function with three-tier scoring - WITH FAILSAFE
    
    Args:
        test_mode: Use test data instead of yesterday's RFPs
        max_rfps: Maximum RFPs to process
        overkill_mode: Skip all filters and process EVERYTHING
        days_back: How many days to look back
    """
    
    print("\n" + "="*70)
    if overkill_mode:
        print("🔥 OVERKILL MODE - PROCESSING ALL RFPS WITHOUT FILTERS")
    else:
        print("🚀 ENHANCED RFP DISCOVERY SYSTEM")
    print("="*70)
    print(f"📊 Qualified Sheet (7-10): .../{Config.SPREADSHEET_ID[-6:]}")
    print(f"🤔 Maybe Sheet (4-6): .../{Config.MAYBE_SPREADSHEET_ID[-6:]}")
    print(f"📋 All RFPs Sheet (1-10): .../{Config.SPAM_SPREADSHEET_ID[-6:]}")
    print("="*70)
    
    # Initialize result collections EARLY so they're available in finally block
    all_results = []
    qualified = []
    maybe = []
    rejected = []
    to_process = []
    candidates_for_deep = []
    rejected_by_mini = []
    to_carryover = []
    adaptive_threshold = 4
    
    # Initialize services (these must be available for finally block)
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    carryover_mgr = CarryoverManager()
    weekend_mgr = WeekendCatchupManager(sam_client)
    
    # Setup all sheets
    setup_all_sheets(sheets_manager)
    
    try:
        # ========== ALL MAIN PROCESSING IN TRY BLOCK ==========
        
        # Get existing Notice IDs from all sheets for duplicate detection
        print("\n🔍 Loading existing Notice IDs for duplicate detection...")
        existing_main_ids = sheets_manager.get_existing_notice_ids(Config.SPREADSHEET_ID) if Config.SPREADSHEET_ID else set()
        existing_maybe_ids = sheets_manager.get_existing_notice_ids(Config.MAYBE_SPREADSHEET_ID) if Config.MAYBE_SPREADSHEET_ID else set()
        existing_spam_ids = sheets_manager.get_existing_notice_ids(Config.SPAM_SPREADSHEET_ID) if Config.SPAM_SPREADSHEET_ID else set()
        
        # Combine all existing IDs for pre-LLM duplicate check
        all_existing_ids = existing_main_ids | existing_maybe_ids | existing_spam_ids
        print(f"  Found {len(all_existing_ids)} existing RFPs across all sheets")
    
        # Check for carryover RFPs
        carryover_stats = carryover_mgr.get_stats()
        if carryover_stats['has_carryover']:
            print(f"\n📦 Found {carryover_stats['count']} carryover RFPs from {carryover_stats['date']}")
    
        # Determine which days to search
        if test_mode:
            days_to_search = [datetime.now().strftime('%m/%d/%Y')]
            print(f"\n🧪 TEST MODE - Searching today: {days_to_search[0]}")
        elif days_back > 1:
            # Custom days back
            days_to_search = []
            for i in range(days_back):
                day = (datetime.now() - timedelta(days=i)).strftime('%m/%d/%Y')
                days_to_search.append(day)
            print(f"\n📅 CUSTOM - Searching {days_back} days: {', '.join(days_to_search)}")
        else:
            days_to_search = weekend_mgr.get_days_to_process()
            if len(days_to_search) > 1:
                print(f"\n📅 MONDAY CATCH-UP MODE")
                print(f"  Will search: {', '.join(days_to_search)}")
            else:
                print(f"\n📅 PRODUCTION - Searching: {days_to_search[0]}")
    
        # Search for RFPs based on mode
        print("\n🔍 Searching SAM.gov...")
        all_opportunities = []
        
        if overkill_mode:
            print("  🔥 OVERKILL MODE - NO FILTERS!")
            for day in days_to_search:
                day_rfps = search_overkill(sam_client, day)
                all_opportunities.extend(day_rfps)
        elif len(days_to_search) > 1:
            # Multiple days
            for day in days_to_search:
                print(f"  Searching {day}...")
                day_rfps = search_broadly(sam_client, day)
                all_opportunities.extend(day_rfps)
                print(f"    Found {len(day_rfps)} RFPs")
        else:
            # Normal single day
            all_opportunities = search_broadly(sam_client, days_to_search[0])
    
        # Light filtering (skip in overkill mode)
        if overkill_mode:
            filtered = all_opportunities
            print(f"\n📊 OVERKILL: Processing ALL {len(all_opportunities)} RFPs - no filtering!")
        else:
            filtered = filter_obvious_irrelevant(all_opportunities)
            print(f"\n📊 Found {len(all_opportunities)} total, {len(filtered)} after filtering")
    
        # Manage daily load with carryover system
        if overkill_mode:
            # In overkill mode, respect max_rfps limit
            if len(filtered) > max_rfps:
                print(f"\n⚠️ OVERKILL: Limiting to {max_rfps} RFPs (found {len(filtered)})")
                to_process = filtered[:max_rfps]
                to_carryover = []  # Don't carryover in overkill mode
            else:
                to_process = filtered
                to_carryover = []
        else:
            to_process, to_carryover = carryover_mgr.manage_daily_load(filtered)
        
        if to_carryover:
            print(f"\n⚠️ HIGH VOLUME DAY DETECTED")
            print(f"  • Processing: {len(to_process)} RFPs today")
            print(f"  • Carrying over: {len(to_carryover)} RFPs to next run")
            print(f"  • These will be processed tomorrow with priority")
    
        # Prioritize RFPs for processing
        to_process = carryover_mgr.prioritize_rfps(to_process)
        
        # Get adaptive threshold based on volume
        adaptive_threshold = carryover_mgr.get_adaptive_threshold(len(to_process))
        if adaptive_threshold > 4:
            print(f"\n📈 Volume adjustment: Using stricter threshold ({adaptive_threshold}) for Phase 1 screening")
    
        # Pre-LLM duplicate check
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
            print(f"  ⚠️ Skipped {duplicates_skipped} duplicates already in sheets")
        
        to_process = to_process_deduped
    
        # ========== PHASE 1: GPT-5-MINI RAPID SCREENING ==========
        print(f"\n⚡ PHASE 1: Rapid screening {len(to_process)} RFPs with GPT-5-mini (15 concurrent)...")
        print("="*70)
        
        # Initialize mini processor with ULTRA high concurrency (2M TPM!)
        mini_processor = ParallelMiniProcessor(Config.OPENAI_API_KEY, max_concurrent=200)
        
        # Quick screen all RFPs (returns those scoring at or above adaptive threshold)
        candidates_for_deep, maybe_from_mini, rejected_by_mini = mini_processor.process_batch(
            to_process, 
            threshold=adaptive_threshold
        )
        
        print(f"\n📊 Mini screening results:")
        print(f"  ✅ {len([c for c in candidates_for_deep if c.get('mini_screen', {}).get('score', 0) >= 7])} high-priority (7-10)")
        print(f"  🤔 {len(maybe_from_mini)} maybe (4-6)")
        print(f"  ❌ {len(rejected_by_mini)} rejected (1-3)")
        print(f"  📋 Total for deep analysis: {len(candidates_for_deep)}")
    
        # ========== PHASE 2: GPT-5 DEEP ANALYSIS ==========
        print(f"\n🔬 PHASE 2: Deep analysis of {len(candidates_for_deep)} promising RFPs with GPT-5 (30 concurrent)...")
        print("="*70)
        
        # Initialize parallel processor with 30 concurrent workers for 450k TPM limits
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
    
        # Sort results into tiers based on DEEP ANALYSIS scores
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
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user - saving partial results...")
        logger.info("Process interrupted - will save partial results")
    except Exception as e:
        print(f"\n\n❌ Error during processing: {str(e)[:200]}")
        logger.error(f"Processing error: {str(e)}", exc_info=True)
    finally:
        # ========== ALWAYS WRITE PARTIAL RESULTS TO SHEETS ==========
        print("\n📝 Writing results to Google Sheets (even if incomplete)...")
        
        # Batch write to ALL RFPs sheet
        if all_results:
            print(f"\n📋 Writing {len(all_results)} RFPs to spam sheet...")
            
            spam_rows = []
            for item in all_results:
                opp = item['opportunity']
                assessment = item['assessment']
            
                # Add screener info to indicate which model was used
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
                logger.error(f"  Error writing to spam sheet: {str(e)[:100]}")
    
        # Write MAYBE opportunities (4-6)
        if maybe:
            print(f"\n🤔 Writing {len(maybe)} maybe RFPs to review sheet...")
            
            maybe_rows = []
            duplicates_in_maybe = 0
            
            for item in maybe:
                opp = item['opportunity']
                assessment = item['assessment']
                notice_id = opp.get('noticeId', '')
                
                # Post-LLM duplicate check for Maybe sheet
                if notice_id and notice_id in existing_maybe_ids:
                    duplicates_in_maybe += 1
                    logger.info(f"Skipping duplicate in maybe sheet: {notice_id}")
                    continue  # Skip adding to maybe sheet
            
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
                if duplicates_in_maybe > 0:
                    print(f"  ⚠️ Skipped {duplicates_in_maybe} duplicates already in maybe sheet")
            except Exception as e:
                logger.error(f"  Error writing to maybe sheet: {str(e)[:100]}")
    
        # Process QUALIFIED opportunities (7-10)
        if qualified:
            print(f"\n✅ Processing {len(qualified)} qualified RFPs...")
            
            duplicates_in_main = 0
            for item in qualified:  # Process ALL qualified RFPs, no limit
                opp = item['opportunity']
                assessment = item['assessment']
                notice_id = opp.get('noticeId', '')
            
                # Post-LLM duplicate check for Main sheet
                if notice_id and notice_id in existing_main_ids:
                    duplicates_in_main += 1
                    logger.info(f"Skipping duplicate in main sheet: {notice_id}")
                    continue  # Skip adding to main sheet
            
                try:
                    # Create Drive folder
                    folder_name = f"{opp.get('noticeId', '')[:20]} - {opp.get('title', '')[:30]}"
                    # Create folder in RFP_Files subfolder instead of main folder
                    folder_id = drive_manager.create_folder(folder_name, Config.DAILY_RFPS_FOLDER_ID)
                
                    # Download and store RFP attachments (PDFs, docs, etc.)
                    print(f"  📎 Downloading attachments for {opp.get('title', '')[:40]}...")
                    stored_files = drive_manager.store_rfp_attachments(opp, folder_id, sam_client)
                    if stored_files:
                        print(f"     Stored {len(stored_files)} documents")
                
                    # Detailed assessment doc
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
                    
                    # Add to main sheet
                    sheets_manager.add_opportunity(
                        Config.SPREADSHEET_ID,
                        opp,
                        assessment,
                        folder_url
                    )
                
                    print(f"  ✓ {opp.get('title', '')[:50]}...")
                    
                except Exception as e:
                    logger.error(f"  Error processing qualified: {str(e)[:100]}")
        
            if duplicates_in_main > 0:
                print(f"  ⚠️ Skipped {duplicates_in_main} duplicates already in main sheet")
    
        # Summary
        print("\n" + "="*70)
        print("📊 DISCOVERY COMPLETE - TWO-PHASE SUMMARY")
        print("="*70)
    
        # Carryover status
        if to_carryover:
            print(f"\n📦 Carryover Status:")
            print(f"  • {len(to_carryover)} RFPs saved for next run")
            print(f"  • Will be processed with priority tomorrow")
    
        print(f"\n⚡ Phase 1 - GPT-5-mini Screening:")
        print(f"  • Total Screened: {len(to_process)}")
        print(f"  • Threshold Used: {adaptive_threshold}")
        print(f"  • Passed to Phase 2: {len(candidates_for_deep)}")
        print(f"  • Rejected Early: {len(rejected_by_mini)}")
        print(f"  • Time Saved: ~{len(rejected_by_mini) * 30}s ({len(rejected_by_mini) * 30 / 60:.1f} minutes)")
    
        print(f"\n🔬 Phase 2 - GPT-5 Deep Analysis:")
        print(f"  • Deep Analyzed: {len(candidates_for_deep)}")
        print(f"  • Qualified (7-10): {len(qualified)} → Main sheet + Drive")
        print(f"  • Maybe (4-6): {len(maybe)} → Review sheet")
        print(f"  • Total Rejected: {len(rejected)} → Spam sheet only")
    
        if all_results:
            avg = sum(r['assessment'].get('relevance_score', 0) for r in all_results) / len(all_results)
            print(f"\n  • Average Score: {avg:.1f}/10")
    
        print(f"\n📂 View Results:")
        print(f"  • Qualified (7-10): https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
        print(f"  • Maybe (4-6): https://docs.google.com/spreadsheets/d/{Config.MAYBE_SPREADSHEET_ID}")
        print(f"  • All RFPs: https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    
        if qualified:
            print(f"  • Documents: https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
        
        print("\n✨ Enhanced discovery complete with three-tier scoring!\n")
        
        # Log health metrics at end
        health_status = health_monitor.check_health()
        if health_status['status'] != 'healthy':
            logger.warning(f"System health status: {health_status['status']}")
            for check_name, check_data in health_status['checks'].items():
                if check_data.get('status') != 'healthy':
                    logger.warning(f"  {check_name}: {check_data}")
        
        # Save metrics to file
        health_monitor.save_metrics('discovery_metrics.json')
    
    # Return statement is outside try/finally - always returns results
    return {
        'qualified': qualified,
        'maybe': maybe,
        'rejected': rejected,
        'total': len(all_results)
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced RFP Discovery')
    parser.add_argument('--test', action='store_true', help='Test mode (search today)')
    parser.add_argument('--max', type=int, default=200, help='Max RFPs to process')
    
    args = parser.parse_args()
    
    enhanced_discovery(test_mode=args.test, max_rfps=args.max)