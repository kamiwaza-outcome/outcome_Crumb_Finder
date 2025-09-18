#!/usr/bin/env python
"""
Test the massive performance improvements with mock data
"""

import sys
import json
import time
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from config import Config
from parallel_mini_processor import ParallelMiniProcessor
from parallel_processor import ParallelProcessor
from ai_qualifier import AIQualifier

def generate_mock_rfps(count=100):
    """Generate mock RFP data for testing"""
    rfps = []
    for i in range(count):
        rfps.append({
            'noticeId': f'TEST-{i:04d}',
            'title': random.choice([
                'AI/ML Development Services',
                'Construction Services', 
                'Data Analytics Platform',
                'Janitorial Services',
                'Software Development',
                'Building Maintenance'
            ]) + f' #{i}',
            'fullParentPathName': 'TEST AGENCY',
            'naicsCode': random.choice(['541511', '541512', '236220']),
            'classificationCode': 'D307',
            'description': 'Lorem ipsum ' * 50,  # Decent sized description
            'uiLink': f'https://sam.gov/test/{i}'
        })
    return rfps

def main():
    print("\n" + "="*70)
    print("🚀 PERFORMANCE TEST: NEW TPM LIMITS")
    print("="*70)
    print(f"Config: {Config.MAX_CONCURRENT_MINI} mini, {Config.MAX_CONCURRENT_DEEP} deep")
    print(f"Tokens: {Config.GPT5_MINI_MAX_TOKENS} mini, {Config.GPT5_MAX_TOKENS} deep")
    
    # Generate test data
    rfp_count = 50
    print(f"\n📊 Generating {rfp_count} mock RFPs...")
    mock_rfps = generate_mock_rfps(rfp_count)
    
    # Test mini screening with 200 concurrent
    print(f"\n🔍 PHASE 1: Mini screening with {Config.MAX_CONCURRENT_MINI} concurrent workers...")
    start_time = time.time()
    
    mini_processor = ParallelMiniProcessor(
        Config.OPENAI_API_KEY, 
        max_concurrent=Config.MAX_CONCURRENT_MINI
    )
    
    # Process with mini screener
    for_deep, maybe, rejected = mini_processor.process_batch(mock_rfps, threshold=4)
    
    mini_time = time.time() - start_time
    print(f"✅ Mini screening complete in {mini_time:.2f}s")
    print(f"  - High priority (7-10): {len([r for r in for_deep if r.get('mini_screen', {}).get('score', 0) >= 7])}")
    print(f"  - Maybe (4-6): {len(maybe)}")
    print(f"  - Rejected (1-3): {len(rejected)}")
    print(f"  - Rate: {rfp_count/mini_time:.1f} RFPs/sec")
    
    # Test deep analysis with 30 concurrent
    if for_deep:
        print(f"\n🔬 PHASE 2: Deep analysis of {len(for_deep)} RFPs with {Config.MAX_CONCURRENT_DEEP} concurrent workers...")
        start_time = time.time()
        
        qualifier = AIQualifier(Config.OPENAI_API_KEY)
        deep_processor = ParallelProcessor(
            qualifier,
            max_concurrent=Config.MAX_CONCURRENT_DEEP
        )
        
        # Process top candidates
        deep_results = deep_processor.process_batch(for_deep[:20])  # Limit to 20 for testing
        
        deep_time = time.time() - start_time
        qualified = len([r for r in deep_results if r.get('assessment', {}).get('relevance_score', 0) >= 7])
        
        print(f"✅ Deep analysis complete in {deep_time:.2f}s")
        print(f"  - Qualified (7-10): {qualified}")
        print(f"  - Rate: {len(deep_results)/deep_time:.1f} RFPs/sec")
    
    print("\n" + "="*70)
    print("✨ PERFORMANCE TEST COMPLETE")
    print(f"Total processing time: {mini_time + (deep_time if for_deep else 0):.2f}s")
    print(f"Throughput: {rfp_count/(mini_time + (deep_time if for_deep else 0)):.1f} RFPs/sec overall")
    print("="*70)

if __name__ == "__main__":
    main()