import logging
from typing import Dict, List, Set
from difflib import SequenceMatcher
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DeduplicationService:
    def __init__(self, sheets_manager):
        self.sheets_manager = sheets_manager
        self._cache = {}
        self._cache_timestamp = {}
        self.cache_ttl = timedelta(minutes=30)  # Cache for 30 minutes
    
    def is_duplicate(self, opportunity: Dict, sheet_id: str) -> bool:
        """Check if opportunity already exists in sheet"""
        
        # Get cached notice IDs or fetch from sheet
        notice_ids = self._get_cached_notice_ids(sheet_id)
        
        # Check exact notice ID match
        opportunity_notice_id = opportunity.get('noticeId', '')
        if opportunity_notice_id and opportunity_notice_id in notice_ids:
            logger.info(f"Duplicate found by notice ID: {opportunity_notice_id}")
            return True
        
        # Check solicitation number if available
        solicitation_number = opportunity.get('solicitationNumber', '')
        if solicitation_number:
            # Need to get full data for solicitation number check
            if self._is_solicitation_duplicate(solicitation_number, sheet_id):
                logger.info(f"Duplicate found by solicitation number: {solicitation_number}")
                return True
        
        # Fuzzy matching on title + agency to catch near-duplicates
        if self._is_fuzzy_duplicate(opportunity, sheet_id):
            logger.info(f"Fuzzy duplicate found for: {opportunity.get('title', '')[:50]}")
            return True
        
        return False
    
    def _get_cached_notice_ids(self, sheet_id: str) -> Set[str]:
        """Get notice IDs with caching"""
        
        now = datetime.now()
        
        # Check if cache is valid
        if sheet_id in self._cache and sheet_id in self._cache_timestamp:
            if now - self._cache_timestamp[sheet_id] < self.cache_ttl:
                return self._cache[sheet_id]
        
        # Fetch fresh data
        notice_ids = set(self.sheets_manager.get_all_notice_ids(sheet_id))
        
        # Update cache
        self._cache[sheet_id] = notice_ids
        self._cache_timestamp[sheet_id] = now
        
        logger.info(f"Refreshed cache with {len(notice_ids)} notice IDs")
        return notice_ids
    
    def _is_solicitation_duplicate(self, solicitation_number: str, sheet_id: str) -> bool:
        """Check if solicitation number exists in sheet"""
        
        try:
            # Get solicitation numbers from sheet (column F)
            result = self.sheets_manager.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Opportunities!F:F'  # Solicitation Number column
            ).execute()
            
            values = result.get('values', [])
            # Skip header row
            solicitation_numbers = [row[0] for row in values[1:] if row and row[0]]
            
            return solicitation_number in solicitation_numbers
            
        except Exception as e:
            logger.error(f"Error checking solicitation numbers: {str(e)}")
            return False
    
    def _is_fuzzy_duplicate(self, opportunity: Dict, sheet_id: str, threshold: float = 0.85) -> bool:
        """Check for fuzzy duplicates based on title and agency similarity"""
        
        try:
            # Get titles and agencies from sheet
            result = self.sheets_manager.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='Opportunities!G:H'  # Title and Agency columns
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:  # Only header or empty
                return False
            
            opp_title = opportunity.get('title', '').lower().strip()
            opp_agency = opportunity.get('fullParentPathName', '').lower().strip()
            
            if not opp_title:
                return False
            
            # Check each existing opportunity
            for row in values[1:]:  # Skip header
                if len(row) >= 2:
                    existing_title = row[0].lower().strip() if row[0] else ''
                    existing_agency = row[1].lower().strip() if len(row) > 1 and row[1] else ''
                    
                    # Calculate similarity
                    title_similarity = SequenceMatcher(None, opp_title, existing_title).ratio()
                    
                    # If titles are very similar
                    if title_similarity >= threshold:
                        # Also check agency if both are available
                        if opp_agency and existing_agency:
                            agency_similarity = SequenceMatcher(None, opp_agency, existing_agency).ratio()
                            if agency_similarity >= 0.7:  # Lower threshold for agency
                                return True
                        else:
                            # If no agency info, rely on title alone with higher threshold
                            if title_similarity >= 0.9:
                                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in fuzzy duplicate check: {str(e)}")
            return False
    
    def clear_cache(self, sheet_id: str = None):
        """Clear the cache"""
        
        if sheet_id:
            self._cache.pop(sheet_id, None)
            self._cache_timestamp.pop(sheet_id, None)
            logger.info(f"Cleared cache for sheet {sheet_id}")
        else:
            self._cache.clear()
            self._cache_timestamp.clear()
            logger.info("Cleared all caches")
    
    def add_to_cache(self, opportunity: Dict, sheet_id: str):
        """Add a newly processed opportunity to cache to avoid re-processing"""
        
        if sheet_id in self._cache:
            notice_id = opportunity.get('noticeId')
            if notice_id:
                self._cache[sheet_id].add(notice_id)
                logger.debug(f"Added {notice_id} to cache")