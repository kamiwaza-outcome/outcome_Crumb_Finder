#!/usr/bin/env python
"""
Full OVERKILL MODE - Process ALL RFPs from August 25th, 2025
With proper error handling and progress tracking
"""

import requests
import json
import time
import sys
from datetime import datetime
from dotenv import load_dotenv
import os

print("Loading environment variables...")
load_dotenv()

# Get API keys
api_key = os.getenv('SAM_API_KEY')
openai_key = os.getenv('OPENAI_API_KEY')

if not api_key or not openai_key:
    print("ERROR: Missing API keys!")
    sys.exit(1)

print("Importing modules...")
from config import Config
from parallel_mini_processor import ParallelMiniProcessor
from parallel_processor import ParallelProcessor
from ai_qualifier import AIQualifier

def fetch_all_rfps_from_august_25():
    """Fetch ALL RFPs from August 25th, 2025"""
    all_rfps = []
    date_str = "08/25/2025"
    base_url = 'https://api.sam.gov/opportunities/v2/search'
    
    print(f"\n🔥 Fetching ALL RFPs from {date_str}...")
    
    # First, get total count
    params = {
        'api_key': api_key,
        'postedFrom': date_str,
        'postedTo': date_str,
        'limit': 1,
        'offset': 0,
        'active': 'true'
    }
    
    response = requests.get(base_url, params=params, timeout=30)
    total = response.json().get('totalRecords', 0)
    print(f"📊 Total RFPs available: {total}")
    
    # Now fetch in batches
    offset = 0
    limit = 100
    
    while offset < total:
        params['limit'] = limit
        params['offset'] = offset
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            if response.status_code == 200:
                batch = response.json().get('opportunitiesData', [])
                all_rfps.extend(batch)
                print(f"  Fetched {offset + len(batch)}/{total} RFPs...")
                offset += limit
                time.sleep(0.5)  # Be nice to API
            else:
                print(f"  Error: {response.status_code}")
                break
        except Exception as e:
            print(f"  Error fetching batch: {e}")
            break
    
    print(f"✅ Successfully fetched {len(all_rfps)} RFPs")
    return all_rfps

def main():
    print("\n" + "="*70)
    print("🔥 FULL OVERKILL MODE - AUGUST 25TH, 2025")
    print("="*70)
    
    # Fetch all RFPs
    start_time = time.time()
    all_rfps = fetch_all_rfps_from_august_25()
    
    if not all_rfps:
        print("❌ No RFPs found!")
        return
    
    fetch_time = time.time() - start_time
    print(f"⏱️  Fetching took {fetch_time:.1f} seconds")
    
    # Process with mini screener
    print(f"\n⚡ PHASE 1: Mini screening {len(all_rfps)} RFPs with {Config.MAX_CONCURRENT_MINI} concurrent workers...")
    mini_start = time.time()
    
    mini_processor = ParallelMiniProcessor(openai_key, max_concurrent=Config.MAX_CONCURRENT_MINI)
    for_deep, maybe, rejected = mini_processor.process_batch(all_rfps, threshold=4)
    
    mini_time = time.time() - mini_start
    
    print(f"\n📊 Mini screening complete in {mini_time:.1f} seconds:")
    print(f"  ✅ High-priority (7-10): {len([r for r in for_deep if r.get('mini_screen', {}).get('score', 0) >= 7])}")
    print(f"  🤔 Maybe (4-6): {len(maybe)}")
    print(f"  ❌ Rejected (1-3): {len(rejected)}")
    print(f"  📋 Total for deep analysis: {len(for_deep)}")
    print(f"  ⚡ Processing rate: {len(all_rfps)/mini_time:.1f} RFPs/sec")
    
    # Deep analysis if needed
    if for_deep:
        print(f"\n🔬 PHASE 2: Deep analysis of {len(for_deep)} RFPs with {Config.MAX_CONCURRENT_DEEP} concurrent workers...")
        deep_start = time.time()
        
        qualifier = AIQualifier(openai_key)
        deep_processor = ParallelProcessor(qualifier, max_concurrent=Config.MAX_CONCURRENT_DEEP)
        
        deep_results = deep_processor.process_batch(for_deep)
        
        deep_time = time.time() - deep_start
        
        # Categorize
        qualified = [r for r in deep_results if r.get('assessment', {}).get('relevance_score', 0) >= 7]
        maybe_deep = [r for r in deep_results if 4 <= r.get('assessment', {}).get('relevance_score', 0) < 7]
        
        print(f"\n📊 Deep analysis complete in {deep_time:.1f} seconds:")
        print(f"  ✅ Qualified (7-10): {len(qualified)}")
        print(f"  🤔 Maybe (4-6): {len(maybe_deep)}")
        print(f"  ⚡ Processing rate: {len(for_deep)/deep_time:.1f} RFPs/sec")
        
        # Show top qualified
        if qualified:
            print(f"\n🏆 TOP QUALIFIED RFPs:")
            for i, rfp in enumerate(qualified[:10], 1):
                title = rfp['opportunity'].get('title', 'Unknown')
                score = rfp['assessment'].get('relevance_score', 0)
                agency = rfp['opportunity'].get('fullParentPathName', 'Unknown')
                print(f"\n  {i}. [{score}/10] {title[:70]}")
                print(f"     Agency: {agency}")
                print(f"     Link: {rfp['opportunity'].get('uiLink', 'N/A')}")
        
        # Write to sheets
        try:
            from sheets_manager import SheetsManager
            print(f"\n📝 Writing to Google Sheets...")
            sheets = SheetsManager()
            
            if qualified:
                sheets.append_to_qualified_sheet(qualified)
                print(f"  ✅ Wrote {len(qualified)} to qualified sheet")
            
            if maybe_deep:
                sheets.append_to_maybe_sheet(maybe_deep)
                print(f"  🤔 Wrote {len(maybe_deep)} to maybe sheet")
        except Exception as e:
            print(f"  ⚠️ Error writing to sheets: {e}")
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n" + "="*70)
    print(f"✨ OVERKILL MODE COMPLETE!")
    print(f"="*70)
    print(f"📊 Final Statistics:")
    print(f"  • Total RFPs processed: {len(all_rfps)}")
    print(f"  • Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"  • Overall rate: {len(all_rfps)/total_time:.1f} RFPs/sec")
    if for_deep:
        print(f"  • Qualified opportunities: {len(qualified)}")
        print(f"  • Success rate: {len(qualified)/len(all_rfps)*100:.1f}%")
    print("="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()