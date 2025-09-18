"""
Parallel RFP Processor - Handles concurrent GPT API calls
"""

import concurrent.futures
import time
import logging
from typing import List, Dict, Tuple
from threading import Semaphore

logger = logging.getLogger(__name__)

class ParallelProcessor:
    def __init__(self, ai_qualifier, max_concurrent=30):
        """
        Initialize parallel processor
        
        Args:
            ai_qualifier: Instance of AIQualifier class
            max_concurrent: Maximum number of concurrent API calls (default 30 - GPT-5 now has 450k TPM!)
        """
        self.qualifier = ai_qualifier
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        self.last_request_time = 0
        self.min_time_between_requests = 0.01  # 10ms between requests - we have 450k TPM now!
        
    def _process_single(self, opportunity: Dict, index: int, total: int) -> Tuple[int, Dict, Dict]:
        """
        Process a single RFP with rate limiting
        
        Returns:
            Tuple of (index, opportunity, assessment)
        """
        try:
            # Acquire semaphore to limit concurrent requests
            with self.semaphore:
                # Ensure minimum time between starting new requests
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_time_between_requests:
                    time.sleep(self.min_time_between_requests - time_since_last)
                self.last_request_time = time.time()
                
                # Log progress
                if index % 10 == 0:
                    logger.info(f"Processing RFP {index}/{total}")
                
                # Process with AI
                assessment = self.qualifier.assess_opportunity(opportunity)
                
                return (index, opportunity, assessment)
                
        except Exception as e:
            logger.error(f"Error processing RFP {index}: {str(e)}")
            # Return with error assessment
            error_assessment = {
                'is_qualified': False,
                'relevance_score': 0,
                'justification': f'Error during processing: {str(e)}',
                'key_requirements': [],
                'kamiwaza_advantages': [],
                'suggested_approach': '',
                'ai_application': '',
                'error': True
            }
            return (index, opportunity, error_assessment)
    
    def process_batch(self, opportunities: List[Dict], start_index: int = 1) -> List[Dict]:
        """
        Process a batch of opportunities in parallel
        
        Args:
            opportunities: List of opportunity dictionaries
            start_index: Starting index for progress display
            
        Returns:
            List of results in order, each containing opportunity and assessment
        """
        total = len(opportunities)
        results = [None] * total  # Pre-allocate results list
        
        logger.info(f"Starting parallel processing of {total} RFPs with {self.max_concurrent} concurrent workers")
        
        # Use ThreadPoolExecutor for I/O-bound tasks (API calls)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all tasks
            futures = []
            for i, opp in enumerate(opportunities):
                future = executor.submit(
                    self._process_single, 
                    opp, 
                    start_index + i,
                    start_index + total - 1
                )
                futures.append((i, future))
                
                # Small delay to avoid overwhelming the API initially
                if i < self.max_concurrent:
                    time.sleep(0.5)
            
            # Collect results as they complete
            completed = 0
            for i, future in futures:
                try:
                    index, opportunity, assessment = future.result(timeout=120)  # 2 minute timeout per request
                    results[i] = {
                        'opportunity': opportunity,
                        'assessment': assessment
                    }
                    completed += 1
                    
                    # Log progress
                    score = assessment.get('relevance_score', 0)
                    title = opportunity.get('title', 'Unknown')[:60]
                    
                    if score >= 7:
                        print(f"  {index:3}. [{score}/10] ✅ {title}")
                    elif score >= 4:
                        print(f"  {index:3}. [{score}/10] 🤔 {title}")
                    else:
                        if index <= start_index + 19:  # Only print first 20 rejected
                            print(f"  {index:3}. [{score}/10] ❌ {title}")
                    
                    # Progress update every 10 items
                    if completed % 10 == 0:
                        print(f"\n[{completed}/{total}] Processed...")
                        
                except concurrent.futures.TimeoutError:
                    logger.error(f"Timeout processing RFP at index {i}")
                    results[i] = {
                        'opportunity': opportunities[i],
                        'assessment': {
                            'is_qualified': False,
                            'relevance_score': 0,
                            'justification': 'Processing timeout',
                            'key_requirements': [],
                            'kamiwaza_advantages': [],
                            'suggested_approach': '',
                            'ai_application': '',
                            'error': True
                        }
                    }
                except Exception as e:
                    logger.error(f"Error collecting result for RFP at index {i}: {str(e)}")
                    results[i] = {
                        'opportunity': opportunities[i],
                        'assessment': {
                            'is_qualified': False,
                            'relevance_score': 0,
                            'justification': f'Error: {str(e)}',
                            'key_requirements': [],
                            'kamiwaza_advantages': [],
                            'suggested_approach': '',
                            'ai_application': '',
                            'error': True
                        }
                    }
        
        # Filter out any None results (shouldn't happen but just in case)
        results = [r for r in results if r is not None]
        
        logger.info(f"Completed parallel processing: {len(results)}/{total} successfully processed")
        
        return results