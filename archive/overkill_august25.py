#!/usr/bin/env python
"""
Direct OVERKILL MODE for August 25th
Bypasses sam_client issues and gets ALL RFPs directly
"""

import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

from config import Config
from parallel_mini_processor import ParallelMiniProcessor  
from parallel_processor import ParallelProcessor
from ai_qualifier import AIQualifier
from sheets_manager import SheetsManager
try:
    from pdf_generator import PDFGenerator
except:
    PDFGenerator = None

def fetch_all_rfps(date_str, max_rfps=None):
    """Fetch ALL RFPs for a given date"""
    all_opportunities = []
    offset = 0
    limit = 100
    
    print(f"\n🔥 OVERKILL MODE - Fetching ALL RFPs for {date_str}")
    
    while True:
        params = {
            'api_key': Config.SAM_API_KEY,
            'postedFrom': date_str,
            'postedTo': date_str,
            'limit': limit,
            'offset': offset,
            'active': 'true'
        }
        
        try:
            response = requests.get(
                Config.SAM_BASE_URL,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                break
                
            data = response.json()
            batch = data.get('opportunitiesData', [])
            
            if not batch:
                break
                
            all_opportunities.extend(batch)
            print(f"  Retrieved {len(batch)} RFPs (total: {len(all_opportunities)})")
            
            # Check if we've hit our limit
            if max_rfps and len(all_opportunities) >= max_rfps:
                all_opportunities = all_opportunities[:max_rfps]
                print(f"  Limiting to {max_rfps} RFPs for testing")
                break
            
            # Check if we have all records
            total = data.get('totalRecords', 0)
            if len(all_opportunities) >= total:
                break
                
            offset += limit
            time.sleep(0.5)  # Be nice to the API
            
        except Exception as e:
            print(f"Error fetching RFPs: {e}")
            break
    
    return all_opportunities

def main():
    print("\n" + "="*70)
    print("🔥 OVERKILL MODE - AUGUST 25TH, 2025")  
    print("="*70)
    
    # Fetch ALL RFPs from August 25th
    date_str = "08/25/2025"
    # Fetch ALL 1646 RFPs
    all_rfps = fetch_all_rfps(date_str)
    
    print(f"\n📊 Total RFPs found: {len(all_rfps)}")
    
    if not all_rfps:
        print("No RFPs found!")
        return
    
    # Initialize processors
    print(f"\n⚡ PHASE 1: Mini screening {len(all_rfps)} RFPs with {Config.MAX_CONCURRENT_MINI} concurrent workers...")
    mini_processor = ParallelMiniProcessor(Config.OPENAI_API_KEY, max_concurrent=Config.MAX_CONCURRENT_MINI)
    
    # Process with mini screener
    for_deep, maybe, rejected = mini_processor.process_batch(all_rfps, threshold=4)
    
    print(f"\n📊 Mini screening results:")
    print(f"  ✅ High-priority (7-10): {len([r for r in for_deep if r.get('mini_screen', {}).get('score', 0) >= 7])}")
    print(f"  🤔 Maybe (4-6): {len(maybe)}")
    print(f"  ❌ Rejected (1-3): {len(rejected)}")
    print(f"  📋 Total for deep analysis: {len(for_deep)}")
    
    # Deep analysis
    if for_deep:
        print(f"\n🔬 PHASE 2: Deep analysis of {len(for_deep)} RFPs with {Config.MAX_CONCURRENT_DEEP} concurrent workers...")
        
        qualifier = AIQualifier(Config.OPENAI_API_KEY)
        deep_processor = ParallelProcessor(qualifier, max_concurrent=Config.MAX_CONCURRENT_DEEP)
        
        # Process all candidates
        deep_results = deep_processor.process_batch(for_deep)
        
        # Categorize results
        qualified = [r for r in deep_results if r.get('assessment', {}).get('relevance_score', 0) >= 7]
        maybe_deep = [r for r in deep_results if 4 <= r.get('assessment', {}).get('relevance_score', 0) < 7]
        rejected_deep = [r for r in deep_results if r.get('assessment', {}).get('relevance_score', 0) < 4]
        
        print(f"\n📊 Deep analysis results:")
        print(f"  ✅ Qualified (7-10): {len(qualified)}")
        print(f"  🤔 Maybe (4-6): {len(maybe_deep)}")
        print(f"  ❌ Rejected (1-3): {len(rejected_deep)}")
        
        # Write to sheets
        if qualified or maybe_deep:
            print(f"\n📝 Writing results to Google Sheets...")
            sheets = SheetsManager()
            
            # Write qualified
            if qualified:
                sheets.append_to_qualified_sheet(qualified)
                print(f"  ✅ Wrote {len(qualified)} to qualified sheet")
                
                # Generate PDFs for qualified (if available)
                if PDFGenerator:
                    try:
                        pdf_gen = PDFGenerator()
                        for result in qualified[:10]:  # Limit to first 10 for now
                            try:
                                pdf_gen.generate_pdf(result)
                            except:
                                pass
                    except:
                        pass
            
            # Write maybe
            if maybe_deep:
                sheets.append_to_maybe_sheet(maybe_deep)
                print(f"  🤔 Wrote {len(maybe_deep)} to maybe sheet")
        
        print(f"\n" + "="*70)
        print(f"✨ OVERKILL COMPLETE!")
        print(f"Processed {len(all_rfps)} total RFPs from August 25th")
        print(f"Found {len(qualified)} qualified opportunities")
        
        # Show top qualified
        if qualified:
            print(f"\nTop Qualified RFPs:")
            for i, rfp in enumerate(qualified[:5], 1):
                title = rfp['opportunity'].get('title', 'Unknown')
                score = rfp['assessment'].get('relevance_score', 0)
                print(f"  {i}. [{score}/10] {title[:80]}")

if __name__ == "__main__":
    main()