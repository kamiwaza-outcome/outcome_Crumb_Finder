"""
Carryover Manager - Handles RFPs that couldn't be processed due to daily limits
Ensures all RFPs eventually get processed even on high-volume days
"""

import json
import os
import logging
import tempfile
import shutil
from typing import List, Dict
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

class CarryoverManager:
    def __init__(self, carryover_file: str = 'carryover_rfps.json'):
        """Initialize the carryover manager"""
        self.carryover_file = carryover_file
        self.max_daily_processing = Config.MAX_DAILY_RFPS  # Use config value
        
    def load_carryover(self) -> List[Dict]:
        """Load any RFPs carried over from previous days"""
        if not os.path.exists(self.carryover_file):
            return []
        
        try:
            with open(self.carryover_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data.get('rfps', []))} carryover RFPs from {data.get('date', 'unknown date')}")
                return data.get('rfps', [])
        except Exception as e:
            logger.error(f"Error loading carryover file: {str(e)}")
            return []
    
    def save_carryover(self, rfps: List[Dict]) -> None:
        """Save RFPs that couldn't be processed today with atomic write"""
        if not rfps:
            self.clear_carryover()
            return
        
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'count': len(rfps),
            'rfps': rfps
        }
        
        try:
            # Write to temporary file first for atomic operation
            dir_path = os.path.dirname(self.carryover_file) or '.'
            with tempfile.NamedTemporaryFile(mode='w', delete=False, 
                                            dir=dir_path, suffix='.tmp') as tmp_file:
                json.dump(data, tmp_file, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # Ensure data is written to disk
                tmp_name = tmp_file.name
            
            # Atomic rename
            shutil.move(tmp_name, self.carryover_file)
            logger.info(f"Saved {len(rfps)} RFPs for carryover to next run")
        except Exception as e:
            logger.error(f"Error saving carryover file: {str(e)}")
            # Clean up temporary file if it exists
            if 'tmp_name' in locals():
                try:
                    os.unlink(tmp_name)
                except:
                    pass
    
    def clear_carryover(self) -> None:
        """Clear the carryover file"""
        if os.path.exists(self.carryover_file):
            try:
                os.remove(self.carryover_file)
                logger.info("Cleared carryover file")
            except Exception as e:
                logger.error(f"Error clearing carryover file: {str(e)}")
    
    def manage_daily_load(self, new_rfps: List[Dict]) -> tuple:
        """
        Manage daily RFP processing load
        
        Returns:
            tuple: (rfps_to_process, rfps_to_carryover)
        """
        # Load any carryover from previous days
        carryover_rfps = self.load_carryover()
        
        # Combine with today's RFPs (carryover gets priority)
        all_rfps = carryover_rfps + new_rfps
        
        # Remove duplicates based on noticeId
        seen_ids = set()
        unique_rfps = []
        for rfp in all_rfps:
            notice_id = rfp.get('noticeId')
            if notice_id and notice_id not in seen_ids:
                seen_ids.add(notice_id)
                unique_rfps.append(rfp)
        
        logger.info(f"Total RFPs to handle: {len(unique_rfps)} ({len(carryover_rfps)} carryover + {len(new_rfps)} new)")
        
        if len(unique_rfps) <= self.max_daily_processing:
            # Can process everything today
            logger.info(f"Processing all {len(unique_rfps)} RFPs today")
            return unique_rfps, []
        else:
            # Need to carry some over
            to_process = unique_rfps[:self.max_daily_processing]
            to_carryover = unique_rfps[self.max_daily_processing:]
            
            logger.warning(f"⚠️ High volume day! Processing {len(to_process)} RFPs, carrying over {len(to_carryover)}")
            
            # Save carryover immediately
            self.save_carryover(to_carryover)
            
            return to_process, to_carryover
    
    def prioritize_rfps(self, rfps: List[Dict]) -> List[Dict]:
        """
        Prioritize RFPs for processing based on relevance indicators
        
        Priority order:
        1. IT/Tech NAICS codes (541xxx)
        2. Has AI/ML/Data keywords in title
        3. Has modern PSC codes (DA/DB/DC series)
        4. Everything else
        """
        priority_1 = []  # IT NAICS
        priority_2 = []  # AI keywords
        priority_3 = []  # Modern PSC
        priority_4 = []  # Others
        
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 
                      'data', 'analytics', 'automation', 'algorithm', 'software',
                      'cloud', 'digital', 'cyber', 'system', 'platform']
        
        modern_psc = ['DA', 'DB', 'DC', 'DD', 'DJ']  # Modern IT PSC prefixes
        
        for rfp in rfps:
            naics = rfp.get('naicsCode', '')
            title = rfp.get('title', '').lower()
            psc = rfp.get('classificationCode') or ''  # Handle None values safely
            
            # Check priority level
            if naics.startswith('541'):
                priority_1.append(rfp)
            elif any(keyword in title for keyword in ai_keywords):
                priority_2.append(rfp)
            elif psc and any(psc.startswith(prefix) for prefix in modern_psc):
                priority_3.append(rfp)
            else:
                priority_4.append(rfp)
        
        # Combine in priority order
        prioritized = priority_1 + priority_2 + priority_3 + priority_4
        
        logger.info(f"Prioritized RFPs: P1={len(priority_1)}, P2={len(priority_2)}, P3={len(priority_3)}, P4={len(priority_4)}")
        
        return prioritized
    
    def get_adaptive_threshold(self, rfp_count: int) -> int:
        """
        Get adaptive threshold for mini screener based on volume
        
        Higher volume = stricter threshold to reduce Phase 2 load
        """
        if rfp_count < 300:
            return 4  # Normal threshold
        elif rfp_count < 600:
            return 5  # Slightly stricter
        elif rfp_count < 1000:
            return 6  # Stricter
        else:
            return 7  # Very strict for 1000+ days
    
    def get_stats(self) -> Dict:
        """Get carryover statistics"""
        if not os.path.exists(self.carryover_file):
            return {'has_carryover': False, 'count': 0}
        
        try:
            with open(self.carryover_file, 'r') as f:
                data = json.load(f)
                return {
                    'has_carryover': True,
                    'count': len(data.get('rfps', [])),
                    'date': data.get('date', 'unknown'),
                    'oldest_deadline': min(
                        (rfp.get('responseDeadLine', '9999-12-31') for rfp in data.get('rfps', [])),
                        default='N/A'
                    )
                }
        except:
            return {'has_carryover': False, 'count': 0}