#!/usr/bin/env python
"""
Daily Sheet Maintenance Runner
Runs after RFP discovery to organize and maintain Google Sheets
"""

import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sheet_maintenance.log')
    ]
)
logger = logging.getLogger(__name__)

from config import Config
from utilities.sheet_organizer import SheetOrganizer

def create_archive_sheets_if_needed(organizer: SheetOrganizer) -> tuple:
    """
    Create archive sheets if they don't exist
    
    Returns:
        Tuple of (graveyard_id, bank_id)
    """
    graveyard_id = Config.GRAVEYARD_SPREADSHEET_ID
    bank_id = Config.BANK_SPREADSHEET_ID
    
    # Create Graveyard sheet if not configured
    if not graveyard_id:
        logger.info("Creating Graveyard archive sheet...")
        graveyard_id = organizer.create_archive_sheet("RFP Graveyard - Expired Opportunities")
        if graveyard_id:
            logger.info(f"Created Graveyard sheet with ID: {graveyard_id}")
            logger.info("Please add GRAVEYARD_SPREADSHEET_ID to your .env file")
    
    # Create Bank sheet if not configured
    if not bank_id:
        logger.info("Creating Bank archive sheet...")
        bank_id = organizer.create_archive_sheet("RFP Bank - Completed Opportunities")
        if bank_id:
            logger.info(f"Created Bank sheet with ID: {bank_id}")
            logger.info("Please add BANK_SPREADSHEET_ID to your .env file")
    
    return graveyard_id, bank_id

def run_maintenance(test_mode: bool = False):
    """
    Run the complete sheet maintenance routine
    
    Args:
        test_mode: If True, run in test mode (no archiving)
    """
    logger.info("="*70)
    logger.info("🔧 GOOGLE SHEETS MAINTENANCE SYSTEM")
    logger.info("="*70)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check required configuration
    if not Config.GOOGLE_SHEETS_CREDS_PATH:
        logger.error("GOOGLE_SHEETS_CREDS_PATH not configured")
        return 1
    
    if not Config.SPREADSHEET_ID:
        logger.error("SPREADSHEET_ID not configured")
        return 1
    
    try:
        # Initialize organizer
        logger.info("Initializing Sheet Organizer...")
        organizer = SheetOrganizer(Config.GOOGLE_SHEETS_CREDS_PATH)
        
        # Get or create archive sheets
        graveyard_id, bank_id = create_archive_sheets_if_needed(organizer)
        
        # Run maintenance on main sheet
        logger.info("\n📋 Processing Main RFP Sheet...")
        logger.info(f"Sheet ID: {Config.SPREADSHEET_ID}")
        
        if test_mode:
            logger.info("TEST MODE: Running status updates and color coding only")
            
            # Update statuses
            status_stats = organizer.update_rfp_statuses(Config.SPREADSHEET_ID)
            logger.info(f"✅ Updated {status_stats['updated']} statuses")
            logger.info(f"  • New → Active: {status_stats['new_to_active']}")
            logger.info(f"  • Active → Expiring: {status_stats['active_to_expiring']}")
            logger.info(f"  • → Expired: {status_stats['expiring_to_expired']}")
            
            # Apply colors
            organizer.apply_status_colors(Config.SPREADSHEET_ID)
            logger.info("✅ Applied status color coding")
            
            organizer.apply_score_colors_and_labels(Config.SPREADSHEET_ID)
            logger.info("✅ Applied score colors and labels")
            
        else:
            # Full maintenance including archival
            summary = organizer.run_full_maintenance(
                main_sheet_id=Config.SPREADSHEET_ID,
                maybe_sheet_id=Config.MAYBE_SPREADSHEET_ID,
                graveyard_sheet_id=graveyard_id,
                bank_sheet_id=bank_id
            )
            
            logger.info("\n📊 MAINTENANCE SUMMARY")
            logger.info("="*50)
            logger.info(f"✅ Statuses updated: {summary['statuses_updated']}")
            logger.info(f"✅ Color coding applied to {summary['colors_applied']} sheets")
            logger.info(f"📦 Archived to Graveyard: {summary['archived_to_graveyard']} RFPs")
            logger.info(f"💰 Archived to Bank: {summary['archived_to_bank']} RFPs")
            
            if summary['errors']:
                logger.warning(f"⚠️ Errors encountered: {len(summary['errors'])}")
                for error in summary['errors']:
                    logger.warning(f"  • {error}")
        
        # Process Maybe sheet if configured
        if Config.MAYBE_SPREADSHEET_ID:
            logger.info("\n📋 Processing Maybe Sheet...")
            logger.info(f"Sheet ID: {Config.MAYBE_SPREADSHEET_ID}")
            
            # Update statuses and colors only - NO ARCHIVING
            status_stats = organizer.update_rfp_statuses(Config.MAYBE_SPREADSHEET_ID)
            logger.info(f"✅ Updated {status_stats['updated']} statuses")
            
            organizer.apply_status_colors(Config.MAYBE_SPREADSHEET_ID)
            organizer.apply_score_colors_and_labels(Config.MAYBE_SPREADSHEET_ID)
            logger.info("✅ Applied color coding")
            # Note: Maybe sheet items are never archived
        
        logger.info("\n="*70)
        logger.info("✨ Sheet maintenance complete!")
        logger.info(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)
        
        return 0
        
    except Exception as e:
        logger.error(f"Critical error during maintenance: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Google Sheets Maintenance System')
    parser.add_argument('--test', action='store_true', 
                       help='Run in test mode (no archiving)')
    parser.add_argument('--create-archives', action='store_true',
                       help='Only create archive sheets if needed')
    
    args = parser.parse_args()
    
    if args.create_archives:
        # Just create archive sheets
        try:
            organizer = SheetOrganizer(Config.GOOGLE_SHEETS_CREDS_PATH)
            graveyard_id, bank_id = create_archive_sheets_if_needed(organizer)
            
            if graveyard_id:
                print(f"Graveyard Sheet ID: {graveyard_id}")
            if bank_id:
                print(f"Bank Sheet ID: {bank_id}")
                
            print("\nAdd these to your .env file:")
            if graveyard_id and not Config.GRAVEYARD_SPREADSHEET_ID:
                print(f"GRAVEYARD_SPREADSHEET_ID={graveyard_id}")
            if bank_id and not Config.BANK_SPREADSHEET_ID:
                print(f"BANK_SPREADSHEET_ID={bank_id}")
                
            return 0
        except Exception as e:
            logger.error(f"Error creating archive sheets: {str(e)}")
            return 1
    
    # Run full maintenance
    return run_maintenance(test_mode=args.test)

if __name__ == "__main__":
    sys.exit(main())