import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import schedule
import time
import pytz
from dotenv import load_dotenv

from config import Config
from src.sam_client import SAMClient
from src.ai_qualifier import AIQualifier
from src.drive_manager import DriveManager
from src.sheets_manager import SheetsManager
from src.slack_notifier import SlackNotifier
from src.deduplication import DeduplicationService
from archive.parallel_mini_processor import ParallelMiniProcessor
from archive.parallel_processor import ParallelProcessor
from src.sanitizer import Sanitizer
from src.health_monitor import health_monitor

# Load environment variables
load_dotenv()

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rfp_discovery.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RFPDiscoverySystem:
    def __init__(self):
        logger.info("Initializing RFP Discovery System...")
        
        # Initialize clients
        self.sam_client = SAMClient(Config.SAM_API_KEY)
        self.qualifier = AIQualifier(Config.OPENAI_API_KEY)
        self.drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
        self.sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
        self.slack_notifier = SlackNotifier(Config.SLACK_WEBHOOK_URL) if Config.SLACK_WEBHOOK_URL else None
        self.dedup_service = DeduplicationService(self.sheets_manager)
        
        # Setup storage
        self.setup_storage()
        
        # Setup spam sheet headers
        if Config.SPAM_SPREADSHEET_ID:
            self.sheets_manager.setup_spam_sheet_headers(Config.SPAM_SPREADSHEET_ID)
            logger.info(f"Spam sheet ready: {Config.SPAM_SPREADSHEET_ID}")
        
        logger.info("RFP Discovery System initialized successfully")
    
    def setup_storage(self):
        """Initialize Google Sheet and Drive folder"""
        
        # Create or get sheet
        spreadsheet_id = Config.SPREADSHEET_ID or os.getenv('SPREADSHEET_ID')
        if spreadsheet_id:
            self.sheet_id = self.sheets_manager.create_or_get_sheet(
                Config.SHEET_NAME,
                spreadsheet_id
            )
        else:
            self.sheet_id = self.sheets_manager.create_or_get_sheet(Config.SHEET_NAME)
        
        self.sheet_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}"
        
        # Get Drive folder ID from config
        self.drive_folder_id = Config.GOOGLE_DRIVE_FOLDER_ID or os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'root')
        
        logger.info(f"Using sheet: {self.sheet_id}")
        logger.info(f"Using Drive folder: {self.drive_folder_id}")
    
    def run_discovery(self):
        """Main discovery workflow - with two-phase AI screening"""
        
        try:
            logger.info("="*50)
            logger.info("Starting daily RFP discovery with two-phase screening")
            logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 1. Fetch opportunities from SAM.gov
            all_opportunities = self.fetch_all_opportunities()
            logger.info(f"Found {len(all_opportunities)} total opportunities from SAM.gov")
            health_monitor.record_rfp_processing('total_searched', len(all_opportunities))
            
            # 2. Check for duplicates
            new_opportunities = []
            for opp in all_opportunities:
                # Sanitize opportunity data
                opp = Sanitizer.sanitize_rfp_data(opp)
                
                if not self.dedup_service.is_duplicate(opp, self.sheet_id):
                    new_opportunities.append(opp)
                    # Add to cache immediately to avoid processing twice in same run
                    self.dedup_service.add_to_cache(opp, self.sheet_id)
            
            logger.info(f"Found {len(new_opportunities)} new opportunities after deduplication")
            
            # 3. Phase 1: GPT-5-mini rapid screening
            logger.info("Phase 1: GPT-5-mini rapid screening...")
            mini_processor = ParallelMiniProcessor(Config.OPENAI_API_KEY, max_concurrent=15)
            
            # Use adaptive threshold based on volume
            threshold = 4 if len(new_opportunities) < 300 else 5 if len(new_opportunities) < 600 else 6
            
            candidates, maybe_rfps, rejected = mini_processor.process_batch(
                new_opportunities,
                threshold=threshold
            )
            
            logger.info(f"Mini screening: {len(candidates)} for deep analysis, {len(rejected)} rejected")
            health_monitor.record_rfp_processing('mini_screened', len(new_opportunities))
            
            # 4. Phase 2: GPT-5 deep analysis for promising candidates
            logger.info("Phase 2: GPT-5 deep analysis...")
            parallel_processor = ParallelProcessor(self.qualifier, max_concurrent=2)
            
            qualified_opportunities = []
            if candidates:
                deep_results = parallel_processor.process_batch(candidates)
                health_monitor.record_rfp_processing('deep_analyzed', len(deep_results))
                
                for result in deep_results:
                    assessment = result['assessment']
                    opp = result['opportunity']
                    score = assessment.get('relevance_score', 0)
                    
                    # Add ALL evaluated RFPs to spam sheet
                    if Config.SPAM_SPREADSHEET_ID:
                        self.sheets_manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, opp, assessment)
                        logger.info(f"  Added to spam sheet with score {score}/10")
                    
                    # Add qualified ones to the qualified list
                    if assessment['is_qualified']:
                        qualified_opportunities.append(result)
                        health_monitor.record_rfp_processing('qualified', 1)
                        logger.info(f"  ✓ Qualified with score {score}/10")
                    else:
                        health_monitor.record_rfp_processing('rejected', 1)
                        logger.info(f"  ✗ Not qualified (score {score}/10)")
            
            # Also add rejected items to spam sheet with mini scores
            for rejected_item in rejected:
                if Config.SPAM_SPREADSHEET_ID:
                    mini_assessment = {
                        'is_qualified': False,
                        'relevance_score': rejected_item.get('mini_screen', {}).get('score', 0),
                        'justification': rejected_item.get('mini_screen', {}).get('reason', 'Rejected by mini screener'),
                        'screener': 'gpt-5-mini'
                    }
                    self.sheets_manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, rejected_item, mini_assessment)
            
            logger.info(f"Qualified {len(qualified_opportunities)} opportunities for {Config.get_company_name()}")
            
            # 4. Process qualified opportunities
            for item in qualified_opportunities:
                try:
                    self.process_opportunity(item)
                except Exception as e:
                    logger.error(f"Error processing opportunity: {str(e)}")
            
            # 5. Send summary notification
            if self.slack_notifier:
                self.slack_notifier.send_daily_summary(
                    len(all_opportunities),
                    len(qualified_opportunities),
                    qualified_opportunities
                )
            
            logger.info("Daily discovery complete")
            logger.info("="*50)
            
            return qualified_opportunities
            
        except Exception as e:
            logger.error(f"Discovery failed: {str(e)}")
            if self.slack_notifier:
                self.slack_notifier.send_error_notification(str(e))
            raise
    
    def fetch_all_opportunities(self) -> List[Dict]:
        """Fetch all opportunities from SAM.gov for the last 24 hours"""
        
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
        today = datetime.now().strftime('%m/%d/%Y')
        
        logger.info(f"Searching for opportunities posted between {yesterday} and {today}")
        
        all_opportunities = []
        
        # Search using NAICS codes
        for naics in Config.get_naics_codes():
            logger.info(f"Searching NAICS code: {naics}")
            opps = self.sam_client.search_by_naics(naics, yesterday, today)
            all_opportunities.extend(opps)
        
        # Search using PSC codes (if configured)
        psc_codes = getattr(Config, 'PSC_CODES', [])
        for psc in psc_codes:
            logger.info(f"Searching PSC code: {psc}")
            opps = self.sam_client.search_by_psc(psc, yesterday, today)
            all_opportunities.extend(opps)
        
        # Search using keywords
        for keyword in Config.get_search_keywords()[:10]:  # Limit to top 10 keywords to avoid rate limits
            logger.info(f"Searching keyword: {keyword}")
            opps = self.sam_client.search_by_keyword(keyword, yesterday, today)
            all_opportunities.extend(opps)
        
        # Deduplicate based on notice ID
        unique_opportunities = {}
        for opp in all_opportunities:
            notice_id = opp.get('noticeId')
            if notice_id and notice_id not in unique_opportunities:
                unique_opportunities[notice_id] = opp
        
        return list(unique_opportunities.values())
    
    def process_opportunity(self, item: Dict):
        """Process a single qualified opportunity"""
        
        opp = item['opportunity']
        assessment = item['assessment']
        
        logger.info(f"Processing opportunity: {opp.get('title', 'Unknown')[:50]}...")
        
        # Create Drive folder for this opportunity
        folder_name = f"{opp.get('solicitationNumber', opp.get('noticeId', 'NO_ID'))} - {opp.get('title', 'Unknown')}"
        folder_id = self.drive_manager.create_folder(folder_name, self.drive_folder_id)
        
        # Store attachments and documents
        stored_files = self.drive_manager.store_rfp_attachments(opp, folder_id, self.sam_client)
        logger.info(f"  Stored {len(stored_files)} files in Drive")
        
        # Get folder URL
        folder_url = self.drive_manager.get_folder_url(folder_id)
        
        # Add to tracking sheet
        self.sheets_manager.add_opportunity(
            self.sheet_id,
            opp,
            assessment,
            folder_url
        )
        logger.info(f"  Added to tracking sheet")
        
        # Send Slack notification for this opportunity
        if self.slack_notifier:
            self.slack_notifier.send_opportunity_notification(
                opp,
                assessment,
                folder_url,
                self.sheet_url
            )
            logger.info(f"  Sent Slack notification")

def run_scheduled_discovery():
    """Wrapper for scheduled runs"""
    
    try:
        system = RFPDiscoverySystem()
        system.run_discovery()
    except Exception as e:
        logger.error(f"Scheduled run failed: {str(e)}")

def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='RFP Discovery System')
    parser.add_argument('--run-now', action='store_true', 
                       help='Run discovery immediately')
    parser.add_argument('--schedule', action='store_true',
                       help='Start scheduled daily runs at 5 PM EST')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode with limited searches')
    
    args = parser.parse_args()
    
    if args.run_now or args.test:
        print("Running discovery now...")
        system = RFPDiscoverySystem()
        
        if args.test:
            # Limit searches in test mode
            # Note: In test mode, searches are limited to first 3 keywords and 2 NAICS codes
            logger.info("Running in test mode with limited searches")
        
        results = system.run_discovery()
        print(f"Discovery complete. Found {len(results)} qualified opportunities.")
    
    elif args.schedule:
        print("Starting scheduled discovery system...")
        print(f"Will run daily at {Config.RUN_TIME} {Config.TIMEZONE}")
        
        # Set timezone
        tz = pytz.timezone(Config.TIMEZONE)
        
        # Schedule the job
        schedule.every().day.at(Config.RUN_TIME).do(run_scheduled_discovery)
        
        # Run the scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()