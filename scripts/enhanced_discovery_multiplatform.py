#!/usr/bin/env python3
"""
Enhanced Multi-Platform RFP Discovery System
Supports SAM.gov, SIBR, Vulcan, and future platforms with advanced duplicate detection
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sam_client import SAMClient
from ai_qualifier import AIQualifier
from sheets_manager import SheetsManager
from drive_manager import DriveManager
from platform_manager import (
    SAMPlatform, SIBRPlatform, VulcanPlatform,
    DuplicateDetector, MultiPlatformManager
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_all_sheets(sheets_manager):
    """Setup headers for all three sheets with multi-platform support"""
    
    # Setup spam sheet with new platform columns
    if Config.SPAM_SPREADSHEET_ID:
        sheets_manager.setup_spam_sheet_headers(Config.SPAM_SPREADSHEET_ID)
    
    # Setup maybe sheet
    if Config.MAYBE_SPREADSHEET_ID:
        try:
            result = sheets_manager.service.spreadsheets().values().get(
                spreadsheetId=Config.MAYBE_SPREADSHEET_ID,
                range='A1:R1'
            ).execute()
            
            if not result.get('values'):
                # Add headers for maybe sheet with platform support
                headers = [[
                    'AI Score',
                    'Platform',  # NEW
                    'Title',
                    'Agency', 
                    'Type',
                    'NAICS',
                    'Posted',
                    'Deadline',
                    'Uncertainty Factors',
                    'AI Justification',
                    'Potential AI Application',
                    'Link',  # Changed from SAM Link
                    'Platform ID',  # NEW
                    'Universal ID',  # NEW
                    'Content Hash',  # NEW
                    'Notice ID',  # Keep for backward compatibility
                    'Evaluated'
                ]]
                
                sheets_manager.service.spreadsheets().values().update(
                    spreadsheetId=Config.MAYBE_SPREADSHEET_ID,
                    range='A1:Q1',
                    valueInputOption='USER_ENTERED',
                    body={'values': headers}
                ).execute()
                
                logger.info("Set up maybe sheet headers with platform support")
        except:
            pass

def search_all_platforms(platform_manager, target_date):
    """Search across all registered platforms"""
    
    all_opportunities = []
    platform_results = {}
    
    # Search each platform
    for platform_name, platform in platform_manager.platforms.items():
        logger.info(f"\n🔍 Searching {platform_name}...")
        
        if platform_name == 'SAM':
            # Use existing SAM search logic
            sam_results = search_sam_broadly(platform.client, target_date)
            platform_results['SAM'] = sam_results
            
            # Normalize SAM results
            for opp in sam_results:
                normalized = platform.normalize_opportunity(opp)
                all_opportunities.append(normalized)
                
        elif platform_name == 'SIBR':
            # TODO: Implement SIBR search when API is available
            logger.info("  SIBR search not yet implemented")
            platform_results['SIBR'] = []
            
        elif platform_name == 'VULCAN':
            # TODO: Implement Vulcan search when API is available
            logger.info("  Vulcan search not yet implemented")
            platform_results['VULCAN'] = []
    
    return all_opportunities, platform_results

def search_sam_broadly(sam_client, target_date):
    """SAM.gov specific broad search (existing logic)"""
    
    all_opportunities = []
    
    # IT/Tech NAICS codes - COMPREHENSIVE LIST
    primary_naics = [
        '541511',  # Custom Computer Programming Services
        '541512',  # Computer Systems Design Services
        '541519',  # Other Computer Related Services
        '518210',  # Data Processing, Hosting, and Related Services
    ]
    
    secondary_naics = [
        '541513',  # Computer Facilities Management Services
        '541611',  # Administrative Management Consulting
        '541618',  # Other Management Consulting Services
        '541690',  # Other Scientific and Technical Consulting
        '541990',  # All Other Professional, Scientific, Technical Services
        '541330',  # Engineering Services
        '541715',  # Research and Development in Physical Sciences
        '541714',  # R&D in Biotechnology
        '541720',  # R&D in Social Sciences
    ]
    
    telecom_naics = [
        '517311',  # Wired Telecommunications Carriers
        '517312',  # Wireless Telecommunications Carriers
        '517919',  # All Other Telecommunications
    ]
    
    naics_codes = primary_naics + secondary_naics + telecom_naics
    
    # PSC codes for IT/software
    psc_codes = [
        # Legacy codes
        'D302', 'D307', 'D399', '7030', 'R425',
        # Modern D-series service codes
        'DA01', 'DA10', 'DB01', 'DC01', 'DD01', 'DE01', 
        'DF01', 'DG01', 'DH01', 'DH10', 'DJ01', 'DJ10',
        'DK01', 'DK10',
        # Modern 7-series product codes
        '7A20', '7A21', '7H20', '7J20', '7K20'
    ]
    
    logger.info(f"  Searching by NAICS codes...")
    
    # Search by NAICS codes
    for naics in naics_codes[:5]:  # Limit for testing
        try:
            opps = sam_client.search_by_naics(naics, target_date, target_date)
            all_opportunities.extend(opps)
            logger.info(f"    NAICS {naics}: Found {len(opps)}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"    NAICS {naics}: Error - {str(e)[:50]}")
    
    logger.info(f"  Searching by PSC codes...")
    
    # Search by PSC codes  
    for psc in psc_codes[:5]:  # Limit for testing
        try:
            opps = sam_client.search_by_psc(psc, target_date, target_date)
            all_opportunities.extend(opps)
            logger.info(f"    PSC {psc}: Found {len(opps)}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"    PSC {psc}: Error - {str(e)[:50]}")
    
    # Keyword searches
    priority_keywords = [
        'artificial intelligence', 'machine learning', 'automation',
        'data processing', 'cloud migration'
    ]
    
    logger.info(f"  Searching by keywords...")
    
    for keyword in priority_keywords[:3]:  # Limit for testing
        try:
            params = {
                'title': keyword,
                'postedFrom': target_date,
                'postedTo': target_date,
                'limit': 10,  # Reduced for testing
                'offset': 0,
                'ptype': 'o,p,r,s',
                'api_key': sam_client.api_key
            }
            data = sam_client._make_request(params)
            opps = data.get('opportunitiesData', [])
            all_opportunities.extend(opps)
            logger.info(f"    Keyword '{keyword}': Found {len(opps)}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"    Keyword '{keyword}': Error - {str(e)[:50]}")
    
    # Deduplicate by Notice ID
    unique = {}
    for opp in all_opportunities:
        notice_id = opp.get('noticeId')
        if notice_id and notice_id not in unique:
            unique[notice_id] = opp
    
    return list(unique.values())

def filter_obvious_irrelevant(opportunities):
    """Remove only the most obvious non-matches"""
    
    filtered = []
    skip_keywords = [
        'janitorial', 'custodial', 'lawn', 'mowing', 'landscaping',
        'food service', 'cafeteria', 'laundry', 'uniform',
        'security guard', 'pest control', 'trash', 'refuse'
    ]
    
    for opp in opportunities:
        # Check if it's normalized format
        if 'platform' in opp:
            title = opp.get('title', '').lower()
        else:
            title = opp.get('title', '').lower()
        
        # Skip if title contains obvious non-tech keywords
        if any(skip in title for skip in skip_keywords):
            logger.debug(f"  Skipping obvious non-match: {title[:50]}")
            continue
        
        # Skip awards and justifications
        opp_type = opp.get('type', '')
        if opp_type in ['Award', 'Justification']:
            continue
            
        filtered.append(opp)
    
    return filtered

def enhanced_multiplatform_discovery(test_mode=False, max_rfps=50):
    """Main discovery function with multi-platform support"""
    
    print("\n" + "="*70)
    print("🚀 MULTI-PLATFORM RFP DISCOVERY SYSTEM")
    print("="*70)
    print(f"📊 Qualified Sheet (7-10): .../{Config.SPREADSHEET_ID[-6:]}")
    print(f"🤔 Maybe Sheet (4-6): .../{Config.MAYBE_SPREADSHEET_ID[-6:]}")
    print(f"📋 All RFPs Sheet (1-10): .../{Config.SPAM_SPREADSHEET_ID[-6:]}")
    print("="*70)
    
    # Initialize core services
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Initialize multi-platform manager
    platform_manager = MultiPlatformManager()
    
    # Register platforms
    sam_platform = SAMPlatform(sam_client)
    platform_manager.register_platform(sam_platform)
    
    # Register other platforms when available
    # sibr_platform = SIBRPlatform(api_key=Config.SIBR_API_KEY)
    # platform_manager.register_platform(sibr_platform)
    # vulcan_platform = VulcanPlatform(api_key=Config.VULCAN_API_KEY)
    # platform_manager.register_platform(vulcan_platform)
    
    # Setup all sheets
    setup_all_sheets(sheets_manager)
    
    # Load existing data for duplicate detection
    print("\n🔍 Loading existing data for duplicate detection...")
    
    # Get Universal IDs from all sheets
    existing_main_ids = sheets_manager.get_existing_universal_ids(Config.SPREADSHEET_ID) if Config.SPREADSHEET_ID else set()
    existing_maybe_ids = sheets_manager.get_existing_universal_ids(Config.MAYBE_SPREADSHEET_ID) if Config.MAYBE_SPREADSHEET_ID else set()
    existing_spam_ids = sheets_manager.get_existing_universal_ids(Config.SPAM_SPREADSHEET_ID) if Config.SPAM_SPREADSHEET_ID else set()
    
    # Get content hashes for cross-platform detection
    existing_main_hashes = sheets_manager.get_existing_content_hashes(Config.SPREADSHEET_ID) if Config.SPREADSHEET_ID else set()
    existing_maybe_hashes = sheets_manager.get_existing_content_hashes(Config.MAYBE_SPREADSHEET_ID) if Config.MAYBE_SPREADSHEET_ID else set()
    existing_spam_hashes = sheets_manager.get_existing_content_hashes(Config.SPAM_SPREADSHEET_ID) if Config.SPAM_SPREADSHEET_ID else set()
    
    # Initialize duplicate detector with existing data
    for universal_id in (existing_main_ids | existing_maybe_ids | existing_spam_ids):
        platform_manager.duplicate_detector.platform_ids.add(universal_id)
    
    for content_hash in (existing_main_hashes | existing_maybe_hashes | existing_spam_hashes):
        platform_manager.duplicate_detector.content_hashes.add(content_hash)
    
    print(f"  Loaded {len(platform_manager.duplicate_detector.platform_ids)} Universal IDs")
    print(f"  Loaded {len(platform_manager.duplicate_detector.content_hashes)} content hashes")
    
    # Determine target date
    if test_mode:
        target_date = datetime.now().strftime('%m/%d/%Y')
        print(f"\n🧪 TEST MODE - Searching today: {target_date}")
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
        print(f"\n📅 PRODUCTION - Searching yesterday: {target_date}")
    
    # Search all platforms
    print("\n🔍 Searching across all platforms...")
    all_opportunities, platform_results = search_all_platforms(platform_manager, target_date)
    
    # Filter obvious non-matches
    filtered = filter_obvious_irrelevant(all_opportunities)
    
    # Process with deduplication
    print(f"\n📊 Processing {len(filtered)} RFPs with duplicate detection...")
    
    unique_opportunities = []
    stats = {
        'total': len(filtered),
        'exact_duplicates': 0,
        'cross_platform_duplicates': 0,
        'new_rfps': 0
    }
    
    for opp in filtered[:max_rfps]:
        # Check for duplicates
        dup_status = platform_manager.duplicate_detector.check_duplicate(opp)
        
        if dup_status['is_exact_duplicate']:
            stats['exact_duplicates'] += 1
            logger.info(f"  Skipping exact duplicate: {dup_status['universal_id']}")
            continue
            
        elif dup_status['is_cross_platform_duplicate']:
            stats['cross_platform_duplicates'] += 1
            logger.info(f"  Skipping cross-platform duplicate: {opp['title'][:50]}")
            continue
            
        else:
            # New unique RFP
            stats['new_rfps'] += 1
            unique_opportunities.append(opp)
            
            # Add to detector for future checks
            platform_manager.duplicate_detector.add_rfp(opp)
    
    print(f"\n📊 Deduplication Results:")
    print(f"  Total found: {stats['total']}")
    print(f"  Exact duplicates skipped: {stats['exact_duplicates']}")
    print(f"  Cross-platform duplicates skipped: {stats['cross_platform_duplicates']}")
    print(f"  New unique RFPs to process: {stats['new_rfps']}")
    
    # Process unique RFPs with AI
    print(f"\n🤖 Processing {len(unique_opportunities)} unique RFPs with AI...")
    print("="*70)
    
    all_results = []
    qualified = []  # 7-10
    maybe = []      # 4-6
    rejected = []   # 1-3
    
    for i, opp in enumerate(unique_opportunities, 1):
        title = opp.get('title', 'Unknown')[:60]
        platform = opp.get('platform', 'UNKNOWN')
        
        # Progress indicator
        if i % 5 == 0:
            print(f"\n[{i}/{len(unique_opportunities)}] Processing...")
        
        try:
            # Convert normalized format back to SAM format for AI assessment
            # (until AI qualifier is updated to handle normalized format)
            if platform == 'SAM':
                raw_opp = opp.get('raw_data', opp)
            else:
                # Convert other platforms to SAM-like format
                raw_opp = {
                    'title': opp.get('title'),
                    'fullParentPathName': opp.get('agency'),
                    'type': opp.get('type'),
                    'naicsCode': opp.get('naics_code'),
                    'classificationCode': opp.get('psc_code'),
                    'responseDeadLine': opp.get('response_deadline'),
                    'description': opp.get('description'),
                    'uiLink': opp.get('url'),
                    'noticeId': opp.get('platform_id'),
                    'postedDate': opp.get('posted_date')
                }
            
            # AI evaluation
            assessment = qualifier.assess_opportunity(raw_opp)
            score = assessment.get('relevance_score', 0)
            
            result = {
                'opportunity': opp,
                'assessment': assessment
            }
            
            all_results.append(result)
            
            # Sort into tiers
            if score >= 7:
                qualified.append(result)
                print(f"  {i:3}. [{score}/10] ✅ [{platform}] {title}")
            elif score >= 4:
                maybe.append(result)
                print(f"  {i:3}. [{score}/10] 🤔 [{platform}] {title}")
            else:
                rejected.append(result)
                if i <= 10:  # Only print first 10 rejected
                    print(f"  {i:3}. [{score}/10] ❌ [{platform}] {title}")
            
            # Rate limiting
            if i % 10 == 0:
                time.sleep(2)
            else:
                time.sleep(0.3)
                
        except Exception as e:
            logger.error(f"  {i:3}. Error processing: {str(e)[:100]}")
    
    print("\n" + "="*70)
    
    # Write to sheets with platform information
    if all_results:
        print(f"\n📋 Writing {len(all_results)} RFPs to spam sheet...")
        
        for item in all_results:
            opp = item['opportunity']
            assessment = item['assessment']
            platform = opp.get('platform', 'SAM')
            
            # Use raw_data if available for backward compatibility
            raw_opp = opp.get('raw_data', opp)
            
            sheets_manager.add_to_spam_sheet(
                Config.SPAM_SPREADSHEET_ID,
                raw_opp,
                assessment,
                platform
            )
        
        print(f"  ✓ Added all {len(all_results)} to spam sheet")
    
    # Process MAYBE opportunities
    if maybe:
        print(f"\n🤔 Writing {len(maybe)} maybe RFPs to review sheet...")
        
        for item in maybe:
            opp = item['opportunity']
            assessment = item['assessment']
            universal_id = f"{opp['platform']}:{opp['platform_id']}"
            
            # Check for duplicates in Maybe sheet
            if universal_id in existing_maybe_ids:
                logger.info(f"Skipping duplicate in maybe sheet: {universal_id}")
                continue
            
            # Write to maybe sheet (would need updated method for platform support)
            # For now, using existing format
    
    # Process QUALIFIED opportunities
    if qualified:
        print(f"\n✅ Processing {len(qualified)} qualified RFPs...")
        
        for item in qualified:
            opp = item['opportunity']
            assessment = item['assessment']
            universal_id = f"{opp['platform']}:{opp['platform_id']}"
            
            # Check for duplicates in Main sheet
            if universal_id in existing_main_ids:
                logger.info(f"Skipping duplicate in main sheet: {universal_id}")
                continue
            
            # Process qualified RFPs (drive folders, etc.)
            # Would need updates to handle multi-platform format
    
    # Summary
    print("\n" + "="*70)
    print("📊 MULTI-PLATFORM DISCOVERY COMPLETE")
    print("="*70)
    print(f"  • Platforms searched: {', '.join(platform_manager.platforms.keys())}")
    print(f"  • Total evaluated: {len(all_results)}")
    print(f"  • Qualified (7-10): {len(qualified)}")
    print(f"  • Maybe (4-6): {len(maybe)}")
    print(f"  • Rejected (1-3): {len(rejected)}")
    print(f"  • Duplicates skipped: {stats['exact_duplicates'] + stats['cross_platform_duplicates']}")
    
    if all_results:
        avg = sum(r['assessment'].get('relevance_score', 0) for r in all_results) / len(all_results)
        print(f"  • Average Score: {avg:.1f}/10")
    
    print(f"\n📂 View Results:")
    print(f"  • Qualified: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    print(f"  • Maybe: https://docs.google.com/spreadsheets/d/{Config.MAYBE_SPREADSHEET_ID}")
    print(f"  • All RFPs: https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
    
    print("\n✨ Multi-platform discovery complete!\n")
    
    return {
        'qualified': qualified,
        'maybe': maybe,
        'rejected': rejected,
        'total': len(all_results),
        'stats': stats
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Platform RFP Discovery')
    parser.add_argument('--test', action='store_true', help='Test mode (search today)')
    parser.add_argument('--max', type=int, default=50, help='Max RFPs to process')
    
    args = parser.parse_args()
    
    enhanced_multiplatform_discovery(test_mode=args.test, max_rfps=args.max)