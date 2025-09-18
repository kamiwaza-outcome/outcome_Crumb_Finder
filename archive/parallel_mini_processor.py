"""
Parallel Mini Processor - ULTRA high-concurrency processing for GPT-5-mini
Optimized for 2,000,000 TPM limit with up to 200 concurrent calls
"""

import concurrent.futures
import time
import logging
from typing import List, Dict, Tuple
from threading import Semaphore, Lock, RLock
from archive.mini_screener import MiniScreener

logger = logging.getLogger(__name__)

class ParallelMiniProcessor:
    def __init__(self, api_key: str, max_concurrent: int = 200):
        """
        Initialize parallel processor for GPT-5-mini
        
        Args:
            api_key: OpenAI API key
            max_concurrent: Maximum concurrent calls (default 200 - mini has 2M TPM!)
        """
        self.screener = MiniScreener(api_key)
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        self.request_lock = RLock()  # Use reentrant lock to prevent deadlocks
        self.last_request_time = 0
        self.min_time_between_requests = 0.005  # Minimal 5ms between starting new requests
        
        # Track token usage
        self.tokens_used = 0
        self.tokens_per_minute_limit = 2000000  # GPT-5-mini NEW limit - 2 MILLION TPM!
        self.token_reset_time = time.time()
        
    def _process_single(self, opportunity: Dict, index: int, total: int) -> Tuple[int, Dict, Dict]:
        """
        Process a single RFP with mini screener
        
        Returns:
            Tuple of (index, opportunity, screening_result)
        """
        try:
            with self.semaphore:
                # Rate limiting between request starts
                with self.request_lock:
                    current_time = time.time()
                    time_since_last = current_time - self.last_request_time
                    if time_since_last < self.min_time_between_requests:
                        time.sleep(self.min_time_between_requests - time_since_last)
                    self.last_request_time = time.time()
                
                # Log progress every 20 items
                if index % 20 == 0:
                    logger.info(f"Mini screening progress: {index}/{total}")
                
                # Quick score with mini model
                result = self.screener.quick_score(opportunity)
                
                # Add result to opportunity
                opportunity['mini_screen'] = result
                
                return (index, opportunity, result)
                
        except Exception as e:
            logger.error(f"Error in mini screening RFP {index}: {str(e)}")
            error_result = {
                'score': 0,
                'reason': f'Error during mini screening: {str(e)}',
                'screener': 'gpt-5-mini',
                'error': True
            }
            opportunity['mini_screen'] = error_result
            return (index, opportunity, error_result)
    
    def process_batch(self, opportunities: List[Dict], threshold: int = 4) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Process a batch of opportunities in parallel with mini screener
        
        Args:
            opportunities: List of opportunity dictionaries
            threshold: Minimum score to pass to deep analysis (default 4)
            
        Returns:
            Tuple of (for_deep_analysis, maybe_category, rejected)
        """
        total = len(opportunities)
        results = [None] * total
        
        logger.info(f"Starting parallel mini screening of {total} RFPs with {self.max_concurrent} concurrent workers")
        logger.info(f"Using threshold of {threshold} for deep analysis")
        
        # Track different categories
        for_deep_analysis = []  # Score 7-10
        maybe_category = []      # Score 4-6
        rejected = []            # Score 1-3
        
        # Use ThreadPoolExecutor for I/O-bound tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all tasks
            futures = []
            for i, opp in enumerate(opportunities):
                future = executor.submit(
                    self._process_single, 
                    opp, 
                    i + 1,
                    total
                )
                futures.append((i, future))
                
                # Tiny delay to avoid overwhelming the API initially
                if i < self.max_concurrent:
                    time.sleep(0.05)
            
            # Collect results as they complete
            completed = 0
            passed = 0
            maybe = 0
            rejected_count = 0
            
            for i, future in futures:
                try:
                    index, opportunity, result = future.result(timeout=30)
                    results[i] = opportunity
                    completed += 1
                    
                    score = result.get('score', 0)
                    
                    # Categorize based on score
                    if score >= 7:
                        for_deep_analysis.append(opportunity)
                        passed += 1
                        logger.debug(f"  [{score}/10] ✅ Passed: {opportunity.get('title', 'Unknown')[:50]}")
                    elif score >= threshold:  # 4-6
                        maybe_category.append(opportunity)
                        maybe += 1
                        logger.debug(f"  [{score}/10] 🤔 Maybe: {opportunity.get('title', 'Unknown')[:50]}")
                    else:  # 1-3
                        rejected.append(opportunity)
                        rejected_count += 1
                        if rejected_count <= 10:  # Only log first 10 rejects
                            logger.debug(f"  [{score}/10] ❌ Rejected: {opportunity.get('title', 'Unknown')[:50]}")
                    
                    # Progress update every 50 items
                    if completed % 50 == 0:
                        logger.info(f"[{completed}/{total}] Mini screened - Passed: {passed}, Maybe: {maybe}, Rejected: {rejected_count}")
                        
                except concurrent.futures.TimeoutError:
                    logger.error(f"Timeout in mini screening at index {i}")
                    if opportunities[i] not in rejected:
                        rejected.append(opportunities[i])
                except Exception as e:
                    logger.error(f"Error collecting mini screening result at index {i}: {str(e)}")
                    if opportunities[i] not in rejected:
                        rejected.append(opportunities[i])
        
        logger.info(f"Mini screening complete: {passed} high-priority (7-10), {maybe} maybe (4-6), {rejected_count} rejected (1-3)")
        
        # Combine high-priority and maybe for deep analysis
        all_for_deep = for_deep_analysis + maybe_category
        logger.info(f"Total for deep analysis: {len(all_for_deep)} RFPs")
        
        return all_for_deep, maybe_category, rejected