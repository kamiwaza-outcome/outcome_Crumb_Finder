import requests
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from config import Config
from src.sanitizer import Sanitizer

logger = logging.getLogger(__name__)

class SAMClient:
    def __init__(self, api_key: str):
        if not api_key or not api_key.strip():
            raise ValueError("SAM API key is required and cannot be empty")
        self.api_key = api_key.strip()
        self.base_url = "https://api.sam.gov/prod/opportunities/v2/search"
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self._request_count = 0
        self._last_request_time = 0
    
    def close(self):
        """Close the session to free resources"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    def _make_request(self, params: Dict) -> Dict:
        """Make API request with retry logic and rate limiting"""
        params['api_key'] = self.api_key
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < Config.MIN_REQUEST_INTERVAL:
            time.sleep(Config.MIN_REQUEST_INTERVAL - time_since_last)
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=Config.SAM_API_TIMEOUT)
            self._last_request_time = time.time()
            self._request_count += 1
            
            # Check rate limit headers proactively
            remaining = response.headers.get('X-RateLimit-Remaining')
            if remaining and int(remaining) < 10:
                reset_time = response.headers.get('X-RateLimit-Reset', '60')
                logger.warning(f"Approaching rate limit. {remaining} requests remaining. Reset in {reset_time}s")
                time.sleep(min(int(reset_time), 60))
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', Config.RETRY_DELAY))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds")
                time.sleep(retry_after)
                raise Exception("Rate limited")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    def search_by_naics(self, naics_code: str, posted_from: str, posted_to: str) -> List[Dict]:
        """Search opportunities by NAICS code"""
        all_opportunities = []
        offset = 0
        limit = 1000
        
        while True:
            params = {
                'ncode': naics_code,
                'postedFrom': posted_from,
                'postedTo': posted_to,
                'limit': limit,
                'offset': offset,
                'ptype': 'o,p,r,g,s'  # Added 's' for special notices
            }
            
            try:
                data = self._make_request(params)
                opportunities = data.get('opportunitiesData', [])
                all_opportunities.extend(opportunities)
                
                if offset + limit >= data.get('totalRecords', 0):
                    break
                    
                offset += limit
                
            except Exception as e:
                logger.error(f"Error searching NAICS {naics_code}: {str(e)}")
                break
        
        logger.info(f"Found {len(all_opportunities)} opportunities for NAICS {naics_code}")
        # Sanitize all RFP data before returning
        return [Sanitizer.sanitize_rfp_data(opp) for opp in all_opportunities]
    
    def search_by_psc(self, psc_code: str, posted_from: str, posted_to: str) -> List[Dict]:
        """Search opportunities by PSC code"""
        all_opportunities = []
        offset = 0
        limit = 1000
        
        while True:
            params = {
                'ccode': psc_code,
                'postedFrom': posted_from,
                'postedTo': posted_to,
                'limit': limit,
                'offset': offset,
                'ptype': 'o,p,r,g,s'  # Added 's' for special notices
            }
            
            try:
                data = self._make_request(params)
                opportunities = data.get('opportunitiesData', [])
                all_opportunities.extend(opportunities)
                
                if offset + limit >= data.get('totalRecords', 0):
                    break
                    
                offset += limit
                
            except Exception as e:
                logger.error(f"Error searching PSC {psc_code}: {str(e)}")
                break
        
        logger.info(f"Found {len(all_opportunities)} opportunities for PSC {psc_code}")
        # Sanitize all RFP data before returning
        return [Sanitizer.sanitize_rfp_data(opp) for opp in all_opportunities]
    
    def search_by_keyword(self, keyword: str, posted_from: str, posted_to: str) -> List[Dict]:
        """Search opportunities by keyword in title (q parameter doesn't work)"""
        all_opportunities = []
        offset = 0
        limit = 100  # SAM.gov typically allows up to 100 per request
        max_results = 1000  # Cap total results per keyword to avoid excessive API calls
        
        while len(all_opportunities) < max_results:
            params = {
                'title': keyword,  # Changed from 'q' to 'title' - the documented parameter
                'postedFrom': posted_from,
                'postedTo': posted_to,
                'limit': limit,
                'offset': offset,
                'ptype': 'o,p,r,s'  # Added 's' for special notices, removed 'g' (awards)
            }
            
            try:
                data = self._make_request(params)
                opportunities = data.get('opportunitiesData', [])
                total_records = data.get('totalRecords', 0)
                
                if not opportunities:
                    # No more results
                    break
                    
                all_opportunities.extend(opportunities)
                
                # Check if we've gotten all available records
                if offset + len(opportunities) >= total_records:
                    break
                    
                # Check if we've hit our max_results cap
                if len(all_opportunities) >= max_results:
                    logger.info(f"  Capped results at {max_results} for keyword '{keyword}'")
                    break
                    
                offset += limit
                
            except Exception as e:
                logger.error(f"Error searching keyword '{keyword}': {str(e)}")
                break
        
        logger.info(f"Found {len(all_opportunities)} opportunities for keyword '{keyword}'")
        # Sanitize all RFP data before returning
        return [Sanitizer.sanitize_rfp_data(opp) for opp in all_opportunities]
    
    def get_opportunity_attachments(self, opportunity: Dict) -> List[Dict]:
        """Get list of attachments for an opportunity"""
        attachments = []
        
        # Check for resource links in the opportunity data
        resource_links = opportunity.get('resourceLinks', [])
        
        if resource_links:
            for link in resource_links:
                # Handle both dict and string formats
                if isinstance(link, dict):
                    attachments.append({
                        'name': link.get('name', 'attachment'),
                        'url': link.get('link', ''),
                        'type': link.get('type', 'document')
                    })
                elif isinstance(link, str):
                    # If it's just a URL string
                    attachments.append({
                        'name': f"attachment_{len(attachments)+1}",
                        'url': link,
                        'type': 'document'
                    })
        
        # Also check for attachment fields
        if opportunity.get('attachments'):
            for attachment in opportunity['attachments']:
                attachments.append({
                    'name': attachment.get('name', 'document'),
                    'url': attachment.get('url', ''),
                    'type': attachment.get('type', 'document')
                })
        
        return attachments
    
    def download_attachment(self, url: str, filename: str) -> bytes:
        """Download an attachment from SAM.gov"""
        try:
            headers = {'Accept': 'application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,*/*'}
            
            # Add API key if needed
            if 'sam.gov' in url and '?' in url:
                url += f"&api_key={self.api_key}"
            elif 'sam.gov' in url:
                url += f"?api_key={self.api_key}"
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error downloading attachment {filename}: {str(e)}")
            return None
    
    def get_opportunity_details(self, opportunity_id: str) -> Optional[Dict]:
        """Get detailed information about a specific opportunity"""
        url = f"https://api.sam.gov/prod/opportunities/v2/search"
        params = {
            'api_key': self.api_key,
            'noticeId': opportunity_id
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            opportunities = data.get('opportunitiesData', [])
            if opportunities:
                return opportunities[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting opportunity details for {opportunity_id}: {str(e)}")
            return None
    
    def download_attachments(self, opportunity_id: str) -> Optional[bytes]:
        """Download all attachments as ZIP"""
        url = f"https://api.sam.gov/opportunities/v1/{opportunity_id}/resources/download/zip"
        params = {'api_key': self.api_key}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading attachments for {opportunity_id}: {str(e)}")
            return None