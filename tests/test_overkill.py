#!/usr/bin/env python3
"""
Test script for OVERKILL MODE
Demonstrates the difference between normal and overkill modes
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sam_client import SAMClient
from enhanced_discovery import search_broadly, search_overkill

def compare_modes():
    """Compare normal vs overkill search results"""
    
    # Initialize SAM client
    sam_client = SAMClient(Config.SAM_API_KEY)
    
    # Test date (yesterday)
    test_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
    
    print("="*60)
    print("🔬 OVERKILL MODE TEST")
    print("="*60)
    print(f"Testing date: {test_date}")
    print()
    
    # Normal mode search
    print("📋 NORMAL MODE (with filters):")
    print("-"*40)
    normal_results = search_broadly(sam_client, test_date)
    print(f"Results: {len(normal_results)} RFPs")
    
    # Show some NAICS codes from normal results
    if normal_results:
        naics_codes = set()
        for rfp in normal_results[:20]:
            naics = rfp.get('naicsCode', 'Unknown')
            if naics:
                naics_codes.add(naics)
        print(f"Sample NAICS codes: {', '.join(list(naics_codes)[:5])}")
    
    print()
    
    # Overkill mode search
    print("🔥 OVERKILL MODE (no filters):")
    print("-"*40)
    overkill_results = search_overkill(sam_client, test_date)
    print(f"Results: {len(overkill_results)} RFPs")
    
    # Show variety of NAICS codes from overkill
    if overkill_results:
        naics_codes = set()
        categories = {}
        for rfp in overkill_results:
            naics = rfp.get('naicsCode', 'Unknown')
            if naics:
                naics_codes.add(naics)
                # Count by first 2 digits (industry sector)
                sector = naics[:2] if len(naics) >= 2 else 'XX'
                categories[sector] = categories.get(sector, 0) + 1
        
        print(f"Unique NAICS codes: {len(naics_codes)}")
        print(f"Sample NAICS codes: {', '.join(list(naics_codes)[:10])}")
        
        # Show top sectors
        print("\nTop industry sectors:")
        for sector, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {sector}xxxx: {count} RFPs")
    
    print()
    print("="*60)
    print("📊 COMPARISON SUMMARY")
    print("="*60)
    print(f"Normal mode:   {len(normal_results):,} RFPs (IT/Tech filtered)")
    print(f"Overkill mode: {len(overkill_results):,} RFPs (EVERYTHING)")
    print(f"Difference:    {len(overkill_results) - len(normal_results):,} additional RFPs")
    
    if normal_results and overkill_results:
        percentage = (len(overkill_results) / len(normal_results) * 100) if normal_results else 0
        print(f"Multiplier:    {percentage:.1f}% of normal")
    
    print()
    print("💡 INSIGHTS:")
    print("- Overkill mode captures ALL government procurement")
    print("- Includes construction, maintenance, food services, etc.")
    print("- May find miscategorized AI/IT opportunities")
    print("- Significantly higher processing cost and time")
    
    return {
        'normal': len(normal_results),
        'overkill': len(overkill_results)
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Overkill Mode')
    parser.add_argument('--quick', action='store_true', help='Just show counts without details')
    args = parser.parse_args()
    
    if args.quick:
        print("\n🚀 Quick test - checking API access...")
        sam_client = SAMClient(Config.SAM_API_KEY)
        test_date = datetime.now().strftime('%m/%d/%Y')
        
        # Just get first page to test
        params = {
            'api_key': Config.SAM_API_KEY,
            'postedFrom': test_date,
            'postedTo': test_date,
            'limit': 10,
            'active': 'true'
        }
        
        response = sam_client._make_request(params)
        if response and response.get('opportunitiesData'):
            print(f"✅ API working! Found {len(response['opportunitiesData'])} RFPs for today")
            print("\nRun without --quick to see full comparison")
        else:
            print("❌ Could not connect to SAM.gov API")
    else:
        compare_modes()