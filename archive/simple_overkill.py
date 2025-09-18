#!/usr/bin/env python
"""
Simple OVERKILL MODE test - fetches and processes RFPs
"""

import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import os
import sys

load_dotenv()

# Get API key
api_key = os.getenv('SAM_API_KEY')
openai_key = os.getenv('OPENAI_API_KEY')

print("\n" + "="*70)
print("🔥 SIMPLE OVERKILL TEST - AUGUST 25TH, 2025")  
print("="*70)

# Fetch first 50 RFPs
date_str = "08/25/2025"
print(f"\n📊 Fetching first 50 RFPs from {date_str}...")

params = {
    'api_key': api_key,
    'postedFrom': date_str,
    'postedTo': date_str,
    'limit': 50,
    'offset': 0,
    'active': 'true'
}

try:
    response = requests.get(
        'https://api.sam.gov/opportunities/v2/search',
        params=params,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        sys.exit(1)
        
    data = response.json()
    rfps = data.get('opportunitiesData', [])
    total = data.get('totalRecords', 0)
    
    print(f"✅ Retrieved {len(rfps)} RFPs (Total available: {total})")
    
    # Show first 5 titles
    print(f"\n📋 Sample RFPs:")
    for i, rfp in enumerate(rfps[:5], 1):
        title = rfp.get('title', 'Unknown')
        print(f"  {i}. {title[:80]}")
    
    # Now process with GPT-5-mini
    print(f"\n⚡ Processing with GPT-5-mini (200 concurrent)...")
    
    from config import Config
    from parallel_mini_processor import ParallelMiniProcessor
    
    mini_processor = ParallelMiniProcessor(openai_key, max_concurrent=200)
    
    # Process batch
    for_deep, maybe, rejected = mini_processor.process_batch(rfps, threshold=4)
    
    print(f"\n📊 Mini screening results:")
    print(f"  ✅ High-priority (7-10): {len([r for r in for_deep if r.get('mini_screen', {}).get('score', 0) >= 7])}")
    print(f"  🤔 Maybe (4-6): {len(maybe)}")
    print(f"  ❌ Rejected (1-3): {len(rejected)}")
    
    # Deep analysis if any passed
    if for_deep:
        print(f"\n🔬 Processing {len(for_deep)} with GPT-5 (30 concurrent)...")
        
        from ai_qualifier import AIQualifier
        from parallel_processor import ParallelProcessor
        
        qualifier = AIQualifier(openai_key)
        deep_processor = ParallelProcessor(qualifier, max_concurrent=30)
        
        deep_results = deep_processor.process_batch(for_deep[:10])  # Limit to 10 for test
        
        qualified = [r for r in deep_results if r.get('assessment', {}).get('relevance_score', 0) >= 7]
        
        print(f"\n✅ Found {len(qualified)} qualified RFPs!")
        
        if qualified:
            print(f"\nTop Qualified:")
            for i, rfp in enumerate(qualified[:3], 1):
                title = rfp['opportunity'].get('title', 'Unknown')
                score = rfp['assessment'].get('relevance_score', 0)
                print(f"  {i}. [{score}/10] {title[:70]}")
    
    print("\n" + "="*70)
    print("✨ Test complete!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()