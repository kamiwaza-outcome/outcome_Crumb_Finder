#!/usr/bin/env python3
"""
Daily RFP Discovery System - Production Ready
Runs at 5PM Eastern to find yesterday's RFPs
Three-tier scoring: Qualified (7-10), Maybe (4-6), All (1-10)
"""

import os
import sys
import schedule
import time
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# Import the enhanced discovery function from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enhanced_discovery import enhanced_discovery

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_discovery.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_daily_discovery():
    """Run the enhanced discovery for yesterday's RFPs"""
    
    # Check if yesterday was a weekend (no government RFPs)
    yesterday = datetime.now() - timedelta(days=1)
    
    # Skip if yesterday was Sunday (we run Saturday to capture Friday)
    if yesterday.weekday() == 6:  # 6=Sunday
        logger.info(f"Skipping run - {yesterday.strftime('%A')} has no government RFPs")
        return
    
    logger.info("="*70)
    logger.info("Starting daily RFP discovery at 5AM Eastern")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Processing RFPs from: {yesterday.strftime('%Y-%m-%d (%A)')}")
    
    try:
        # Run discovery for yesterday's RFPs (production mode)
        # OVERKILL MODE by default - process ALL RFPs found
        results = enhanced_discovery(test_mode=False, overkill_mode=True, max_rfps=5000)
        
        logger.info(f"Daily discovery completed successfully")
        logger.info(f"Qualified: {len(results['qualified'])}, Maybe: {len(results['maybe'])}, Total: {results['total']}")
        
        # Could add email notification here if desired
        
    except Exception as e:
        logger.error(f"Daily discovery failed: {str(e)}")
        # Could add error notification here

def test_run():
    """Test run with today's data"""
    logger.info("Running test discovery with today's data...")
    
    try:
        results = enhanced_discovery(test_mode=True, max_rfps=20)
        logger.info(f"Test completed. Found {results['total']} RFPs")
        return results
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return None

def start_scheduler():
    """Start the daily scheduler for 5AM Eastern"""
    
    # Set timezone to Eastern
    eastern = pytz.timezone('America/New_York')
    
    # Schedule daily run at 5AM Eastern
    schedule.every().day.at("05:00").do(run_daily_discovery)
    
    logger.info("="*70)
    logger.info("🚀 RFP DISCOVERY SCHEDULER STARTED")
    logger.info("="*70)
    logger.info("Will run daily at 5:00 AM Eastern Time")
    logger.info("Runs Tuesday-Saturday (Saturday captures Friday RFPs)")
    logger.info("Automatically skips Sunday (no government RFPs)")
    logger.info(f"Current time: {datetime.now(eastern).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*70)
    
    # Run scheduler
    while True:
        try:
            schedule.run_pending()
            
            # Show next run time every hour
            if datetime.now().minute == 0:
                next_run = schedule.next_run()
                if next_run:
                    logger.info(f"Next run scheduled for: {next_run}")
            
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            logger.info("\nScheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Daily RFP Discovery System')
    parser.add_argument('--test', action='store_true', help='Run a test discovery now')
    parser.add_argument('--schedule', action='store_true', help='Start the daily scheduler')
    parser.add_argument('--once', action='store_true', help='Run once for yesterday')
    parser.add_argument('--overkill', action='store_true', help='OVERKILL MODE: Process ALL RFPs without filters')
    parser.add_argument('--max-rfps', type=int, default=None, help='Maximum RFPs to process')
    parser.add_argument('--days-back', type=int, default=1, help='Days to look back (default 1)')
    
    args = parser.parse_args()
    
    if args.test:
        print("\n🧪 Running test discovery...")
        test_run()
    elif args.once:
        if args.overkill:
            print("\n🔥 OVERKILL MODE ACTIVATED - Processing ALL RFPs!")
            print(f"Max RFPs: {args.max_rfps or 3000}")
            print(f"Days back: {args.days_back}")
        else:
            print("\n📅 Running discovery with filters...")
        
        # Pass parameters to enhanced_discovery
        results = enhanced_discovery(
            test_mode=False,
            overkill_mode=args.overkill,
            max_rfps=args.max_rfps or (3000 if args.overkill else 500),
            days_back=args.days_back
        )
        logger.info(f"Discovery completed. Qualified: {len(results['qualified'])}, Total: {results['total']}")
    elif args.schedule:
        start_scheduler()
    else:
        print("\nRFP Discovery System")
        print("=" * 40)
        print("\nOptions:")
        print("  --test     Run a test with today's RFPs")
        print("  --once     Run once for yesterday's RFPs")
        print("  --schedule Start daily scheduler (5PM ET)")
        print("\nExample:")
        print("  python daily_discovery.py --schedule")
        print()