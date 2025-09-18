"""
Weekend Catch-up Manager - Handles processing multiple days of RFPs
Ensures weekend RFPs are processed on Monday
"""

import logging
import sys
import os
from typing import List, Dict
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sam_client import SAMClient

logger = logging.getLogger(__name__)

class WeekendCatchupManager:
    def __init__(self, sam_client: SAMClient):
        """Initialize weekend catchup manager"""
        self.sam_client = sam_client
        
    def get_days_to_process(self) -> List[str]:
        """
        Determine which days need to be processed
        
        Returns:
            List of dates in MM/DD/YYYY format to process
        """
        today = datetime.now()
        weekday = today.weekday()  # 0=Monday, 6=Sunday
        
        days_to_process = []
        
        if weekday == 0:  # Monday - process Friday, Saturday, Sunday
            logger.info("Monday detected - will process Friday, Saturday, and Sunday RFPs")
            days_to_process = [
                (today - timedelta(days=3)).strftime('%m/%d/%Y'),  # Friday
                (today - timedelta(days=2)).strftime('%m/%d/%Y'),  # Saturday
                (today - timedelta(days=1)).strftime('%m/%d/%Y'),  # Sunday
            ]
        elif weekday == 6:  # Sunday - skip (no government RFPs)
            logger.info("Sunday detected - skipping (no government RFPs posted)")
            return []
        else:  # Tuesday-Saturday - process yesterday only
            days_to_process = [
                (today - timedelta(days=1)).strftime('%m/%d/%Y')
            ]
        
        return days_to_process
    
    def search_multiple_days(self, search_function, days: List[str]) -> List[Dict]:
        """
        Search for RFPs across multiple days
        
        Args:
            search_function: The search function to use (e.g., search_broadly)
            days: List of dates to search in MM/DD/YYYY format
            
        Returns:
            Combined list of all RFPs from all days
        """
        all_rfps = []
        
        for day in days:
            logger.info(f"Searching for RFPs from {day}...")
            day_rfps = search_function(self.sam_client, day)
            all_rfps.extend(day_rfps)
            logger.info(f"  Found {len(day_rfps)} RFPs for {day}")
        
        # Deduplicate based on noticeId
        unique = {}
        for rfp in all_rfps:
            notice_id = rfp.get('noticeId')
            if notice_id and notice_id not in unique:
                unique[notice_id] = rfp
        
        logger.info(f"Total unique RFPs from {len(days)} days: {len(unique)}")
        
        return list(unique.values())
    
    def should_run_catchup(self) -> bool:
        """
        Check if we should run catch-up mode
        
        Returns:
            True if it's Monday and we need to catch up on weekend RFPs
        """
        return datetime.now().weekday() == 0  # Monday
    
    def get_catchup_summary(self, days: List[str]) -> str:
        """
        Get a summary message for catch-up processing
        
        Args:
            days: List of dates being processed
            
        Returns:
            Summary message string
        """
        if len(days) == 1:
            return f"Processing RFPs from {days[0]}"
        elif len(days) == 3:
            return f"Monday catch-up: Processing RFPs from Friday ({days[0]}), Saturday ({days[1]}), and Sunday ({days[2]})"
        else:
            return f"Processing RFPs from {', '.join(days)}"
    
    def estimate_processing_time(self, rfp_count: int, phase1_concurrent: int = 15, phase2_concurrent: int = 2) -> Dict:
        """
        Estimate processing time for a given number of RFPs
        
        Args:
            rfp_count: Number of RFPs to process
            phase1_concurrent: Concurrent workers for Phase 1 (GPT-5-mini)
            phase2_concurrent: Concurrent workers for Phase 2 (GPT-5)
            
        Returns:
            Dictionary with time estimates
        """
        # Phase 1: All RFPs through mini screener
        phase1_time = (rfp_count / phase1_concurrent) * 2  # ~2 seconds per batch
        
        # Phase 2: Assume 30% pass to deep analysis
        phase2_count = int(rfp_count * 0.3)
        phase2_time = (phase2_count / phase2_concurrent) * 30  # ~30 seconds per batch
        
        total_time = phase1_time + phase2_time
        
        return {
            'total_rfps': rfp_count,
            'phase1_time_seconds': phase1_time,
            'phase2_rfps': phase2_count,
            'phase2_time_seconds': phase2_time,
            'total_time_seconds': total_time,
            'total_time_minutes': total_time / 60,
            'estimated_completion': (datetime.now() + timedelta(seconds=total_time)).strftime('%I:%M %p')
        }