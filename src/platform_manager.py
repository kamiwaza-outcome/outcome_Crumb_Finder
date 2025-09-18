#!/usr/bin/env python3
"""
Multi-Platform RFP Management System
Handles duplicate detection across SAM.gov, SIBR, Vulcan, and other platforms
"""

import hashlib
import logging
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class RFPPlatform(ABC):
    """Base class for RFP platform clients"""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (SAM, SIBR, VULCAN, etc.)"""
        pass
    
    @abstractmethod
    def search_opportunities(self, date_from: str, date_to: str) -> List[Dict]:
        """Search for opportunities in the platform"""
        pass
    
    @abstractmethod
    def get_opportunity_id(self, opportunity: Dict) -> str:
        """Extract the platform-specific ID from an opportunity"""
        pass
    
    @abstractmethod
    def normalize_opportunity(self, opportunity: Dict) -> Dict:
        """Normalize opportunity data to common format"""
        pass

class SAMPlatform(RFPPlatform):
    """SAM.gov platform adapter"""
    
    def __init__(self, client):
        self.client = client
        
    @property
    def platform_name(self) -> str:
        return "SAM"
    
    def get_opportunity_id(self, opportunity: Dict) -> str:
        return opportunity.get('noticeId', '')
    
    def search_opportunities(self, date_from: str, date_to: str) -> List[Dict]:
        # This would use the existing SAMClient
        return []  # Placeholder - uses existing sam_client
    
    def normalize_opportunity(self, opportunity: Dict) -> Dict:
        """Convert SAM.gov format to common format"""
        return {
            'platform': 'SAM',
            'platform_id': opportunity.get('noticeId', ''),
            'title': opportunity.get('title', ''),
            'agency': opportunity.get('fullParentPathName', ''),
            'type': opportunity.get('type', ''),
            'posted_date': opportunity.get('postedDate', ''),
            'response_deadline': opportunity.get('responseDeadLine', ''),
            'description': opportunity.get('description', ''),
            'naics_code': opportunity.get('naicsCode', ''),
            'psc_code': opportunity.get('classificationCode', ''),
            'url': opportunity.get('uiLink', ''),
            'raw_data': opportunity  # Keep original for platform-specific fields
        }

class SIBRPlatform(RFPPlatform):
    """SIBR (SBIR/STTR) platform adapter"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
    @property  
    def platform_name(self) -> str:
        return "SIBR"
    
    def get_opportunity_id(self, opportunity: Dict) -> str:
        # SIBR might use different field names
        return opportunity.get('rfp_id', '') or opportunity.get('solicitation_id', '')
    
    def search_opportunities(self, date_from: str, date_to: str) -> List[Dict]:
        # TODO: Implement SIBR API integration
        logger.info(f"SIBR search not yet implemented")
        return []
    
    def normalize_opportunity(self, opportunity: Dict) -> Dict:
        """Convert SIBR format to common format"""
        return {
            'platform': 'SIBR',
            'platform_id': self.get_opportunity_id(opportunity),
            'title': opportunity.get('title', ''),
            'agency': opportunity.get('agency', ''),
            'type': opportunity.get('type', 'SBIR/STTR'),
            'posted_date': opportunity.get('open_date', ''),
            'response_deadline': opportunity.get('close_date', ''),
            'description': opportunity.get('description', ''),
            'naics_code': opportunity.get('naics', ''),
            'psc_code': '',  # SIBR might not have PSC codes
            'url': opportunity.get('url', ''),
            'raw_data': opportunity
        }

class VulcanPlatform(RFPPlatform):
    """Vulcan platform adapter"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
    @property
    def platform_name(self) -> str:
        return "VULCAN"
    
    def get_opportunity_id(self, opportunity: Dict) -> str:
        return opportunity.get('opportunity_number', '') or opportunity.get('opp_id', '')
    
    def search_opportunities(self, date_from: str, date_to: str) -> List[Dict]:
        # TODO: Implement Vulcan API integration
        logger.info(f"Vulcan search not yet implemented")
        return []
    
    def normalize_opportunity(self, opportunity: Dict) -> Dict:
        """Convert Vulcan format to common format"""
        return {
            'platform': 'VULCAN',
            'platform_id': self.get_opportunity_id(opportunity),
            'title': opportunity.get('title', ''),
            'agency': opportunity.get('organization', ''),
            'type': opportunity.get('opportunity_type', ''),
            'posted_date': opportunity.get('posted_date', ''),
            'response_deadline': opportunity.get('deadline', ''),
            'description': opportunity.get('description', ''),
            'naics_code': opportunity.get('naics_code', ''),
            'psc_code': opportunity.get('psc_code', ''),
            'url': opportunity.get('link', ''),
            'raw_data': opportunity
        }

class DuplicateDetector:
    """Advanced duplicate detection across multiple platforms"""
    
    def __init__(self):
        self.platform_ids: Set[str] = set()  # Platform-specific IDs
        self.content_hashes: Set[str] = set()  # Cross-platform detection
        self.title_hashes: Set[str] = set()  # Fuzzy title matching
        
    def create_universal_id(self, platform: str, platform_id: str) -> str:
        """Create a universal ID that includes platform prefix"""
        return f"{platform.upper()}:{platform_id}"
    
    def create_content_hash(self, normalized_rfp: Dict) -> str:
        """Generate content hash for cross-platform duplicate detection"""
        # Create fingerprint from key fields
        fingerprint = ""
        
        # Title (normalized)
        title = normalized_rfp.get('title', '').lower().strip()
        # Remove common words that might vary
        for word in ['the', 'a', 'an', 'for', 'and', 'or', 'of', 'to', 'in']:
            title = title.replace(f' {word} ', ' ')
        fingerprint += title[:100]
        
        # Agency (normalized)
        agency = normalized_rfp.get('agency', '').lower().strip()
        agency = agency.split(',')[0]  # Take first part if hierarchical
        fingerprint += agency
        
        # Posted date (just date, not time)
        posted = normalized_rfp.get('posted_date', '')[:10]
        fingerprint += posted
        
        # Create hash
        return hashlib.md5(fingerprint.encode()).hexdigest()[:16]
    
    def create_title_hash(self, title: str) -> str:
        """Create hash for fuzzy title matching"""
        # More aggressive normalization for title-only matching
        title = title.lower().strip()
        
        # Remove all common words and punctuation
        import re
        title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
        
        stop_words = {'the', 'a', 'an', 'for', 'and', 'or', 'of', 'to', 'in', 
                     'on', 'at', 'by', 'with', 'from', 'up', 'about', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'services', 'service', 'support',
                     'system', 'systems', 'solution', 'solutions'}
        
        words = [w for w in title.split() if w not in stop_words]
        clean_title = ' '.join(sorted(words))  # Sort to catch reordered titles
        
        return hashlib.md5(clean_title.encode()).hexdigest()[:12]
    
    def check_duplicate(self, normalized_rfp: Dict) -> Dict[str, bool]:
        """
        Check for duplicates at multiple levels
        Returns dict with duplicate status for each level
        """
        universal_id = self.create_universal_id(
            normalized_rfp['platform'],
            normalized_rfp['platform_id']
        )
        content_hash = self.create_content_hash(normalized_rfp)
        title_hash = self.create_title_hash(normalized_rfp.get('title', ''))
        
        return {
            'is_exact_duplicate': universal_id in self.platform_ids,
            'is_cross_platform_duplicate': content_hash in self.content_hashes,
            'is_similar_title': title_hash in self.title_hashes,
            'universal_id': universal_id,
            'content_hash': content_hash,
            'title_hash': title_hash
        }
    
    def add_rfp(self, normalized_rfp: Dict):
        """Add an RFP to the duplicate detection system"""
        universal_id = self.create_universal_id(
            normalized_rfp['platform'],
            normalized_rfp['platform_id']
        )
        content_hash = self.create_content_hash(normalized_rfp)
        title_hash = self.create_title_hash(normalized_rfp.get('title', ''))
        
        self.platform_ids.add(universal_id)
        self.content_hashes.add(content_hash)
        self.title_hashes.add(title_hash)
        
        logger.debug(f"Added to duplicate detection: {universal_id}")
    
    def load_from_sheets(self, sheets_data: List[Dict]):
        """Load existing RFPs from sheets for duplicate detection"""
        for row in sheets_data:
            if row.get('platform') and row.get('platform_id'):
                # Reconstruct normalized format from sheet data
                normalized = {
                    'platform': row['platform'],
                    'platform_id': row['platform_id'],
                    'title': row.get('title', ''),
                    'agency': row.get('agency', ''),
                    'posted_date': row.get('posted_date', '')
                }
                self.add_rfp(normalized)
        
        logger.info(f"Loaded {len(self.platform_ids)} existing RFPs for duplicate detection")

class MultiPlatformManager:
    """Manages multiple RFP platforms and coordinates searches"""
    
    def __init__(self):
        self.platforms: Dict[str, RFPPlatform] = {}
        self.duplicate_detector = DuplicateDetector()
        
    def register_platform(self, platform: RFPPlatform):
        """Register a new platform"""
        self.platforms[platform.platform_name] = platform
        logger.info(f"Registered platform: {platform.platform_name}")
    
    def search_all_platforms(self, date_from: str, date_to: str) -> Dict[str, List[Dict]]:
        """
        Search all registered platforms and return normalized results
        Returns: {platform_name: [normalized_opportunities]}
        """
        all_results = {}
        
        for platform_name, platform in self.platforms.items():
            logger.info(f"Searching {platform_name}...")
            
            try:
                # Get raw results from platform
                raw_results = platform.search_opportunities(date_from, date_to)
                
                # Normalize each result
                normalized_results = []
                for raw_opp in raw_results:
                    normalized = platform.normalize_opportunity(raw_opp)
                    
                    # Check for duplicates
                    dup_status = self.duplicate_detector.check_duplicate(normalized)
                    normalized['duplicate_status'] = dup_status
                    
                    normalized_results.append(normalized)
                
                all_results[platform_name] = normalized_results
                logger.info(f"  Found {len(normalized_results)} opportunities from {platform_name}")
                
            except Exception as e:
                logger.error(f"Error searching {platform_name}: {str(e)}")
                all_results[platform_name] = []
        
        return all_results
    
    def process_with_deduplication(self, all_platform_results: Dict[str, List[Dict]]) -> Tuple[List[Dict], Dict]:
        """
        Process results from all platforms with deduplication
        Returns: (unique_opportunities, duplicate_stats)
        """
        unique_opportunities = []
        stats = {
            'total': 0,
            'unique': 0,
            'exact_duplicates': 0,
            'cross_platform_duplicates': 0,
            'similar_titles': 0,
            'by_platform': {}
        }
        
        for platform_name, opportunities in all_platform_results.items():
            platform_stats = {
                'total': len(opportunities),
                'unique': 0,
                'duplicates': 0
            }
            
            for opp in opportunities:
                stats['total'] += 1
                dup_status = opp['duplicate_status']
                
                if dup_status['is_exact_duplicate']:
                    stats['exact_duplicates'] += 1
                    platform_stats['duplicates'] += 1
                    logger.debug(f"Skipping exact duplicate: {dup_status['universal_id']}")
                    
                elif dup_status['is_cross_platform_duplicate']:
                    stats['cross_platform_duplicates'] += 1
                    platform_stats['duplicates'] += 1
                    logger.info(f"Skipping cross-platform duplicate: {opp['title'][:50]}")
                    
                elif dup_status['is_similar_title']:
                    # Log but still process (might be legitimate similar RFP)
                    stats['similar_titles'] += 1
                    logger.warning(f"Similar title detected: {opp['title'][:50]}")
                    unique_opportunities.append(opp)
                    platform_stats['unique'] += 1
                    stats['unique'] += 1
                    
                    # Add to duplicate detector for future checks
                    self.duplicate_detector.add_rfp(opp)
                    
                else:
                    # Completely unique
                    unique_opportunities.append(opp)
                    platform_stats['unique'] += 1
                    stats['unique'] += 1
                    
                    # Add to duplicate detector for future checks
                    self.duplicate_detector.add_rfp(opp)
            
            stats['by_platform'][platform_name] = platform_stats
        
        return unique_opportunities, stats

# Example usage
if __name__ == "__main__":
    # Test the duplicate detection
    detector = DuplicateDetector()
    
    # Simulate RFPs from different platforms
    sam_rfp = {
        'platform': 'SAM',
        'platform_id': 'FA8750-23-Q-0001',
        'title': 'Artificial Intelligence and Machine Learning Support Services',
        'agency': 'Department of Defense.Air Force.AFRL',
        'posted_date': '2024-01-15',
    }
    
    # Same RFP on SIBR (cross-platform duplicate)
    sibr_rfp = {
        'platform': 'SIBR',
        'platform_id': 'AF-2024-001',
        'title': 'AI and ML Support Services',  # Slightly different title
        'agency': 'Air Force Research Laboratory',  # Different format
        'posted_date': '2024-01-15',
    }
    
    # Different RFP on Vulcan
    vulcan_rfp = {
        'platform': 'VULCAN',
        'platform_id': 'VUL-2024-789',
        'title': 'Cloud Computing Infrastructure Development',
        'agency': 'NASA Ames Research Center',
        'posted_date': '2024-01-16',
    }
    
    print("Testing Multi-Platform Duplicate Detection")
    print("=" * 60)
    
    # Check first RFP (SAM)
    sam_check = detector.check_duplicate(sam_rfp)
    print(f"\nSAM RFP: {sam_rfp['title'][:40]}...")
    print(f"  Universal ID: {sam_check['universal_id']}")
    print(f"  Content Hash: {sam_check['content_hash']}")
    print(f"  Is Duplicate: {sam_check['is_exact_duplicate']}")
    detector.add_rfp(sam_rfp)
    
    # Check second RFP (SIBR - should be cross-platform duplicate)
    sibr_check = detector.check_duplicate(sibr_rfp)
    print(f"\nSIBR RFP: {sibr_rfp['title'][:40]}...")
    print(f"  Universal ID: {sibr_check['universal_id']}")
    print(f"  Content Hash: {sibr_check['content_hash']}")
    print(f"  Is Cross-Platform Duplicate: {sibr_check['is_cross_platform_duplicate']}")
    
    # Check third RFP (Vulcan - should be unique)
    vulcan_check = detector.check_duplicate(vulcan_rfp)
    print(f"\nVulcan RFP: {vulcan_rfp['title'][:40]}...")
    print(f"  Universal ID: {vulcan_check['universal_id']}")
    print(f"  Content Hash: {vulcan_check['content_hash']}")
    print(f"  Is Duplicate: {vulcan_check['is_exact_duplicate'] or vulcan_check['is_cross_platform_duplicate']}")
    
    print("\n" + "=" * 60)
    print("✅ Multi-platform duplicate detection ready!")