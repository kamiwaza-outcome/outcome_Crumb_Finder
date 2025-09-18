#!/usr/bin/env python3
"""Show RFPs found without AI evaluation"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from config import Config
from sam_client import SAMClient

def show_rfps():
    print("\n📋 SHOWING RFPs (Without AI Evaluation)\n")
    print("=" * 80)
    
    sam_client = SAMClient(Config.SAM_API_KEY)
    
    # Search last 2 days  
    search_from = (datetime.now() - timedelta(days=2)).strftime('%m/%d/%Y')
    search_to = datetime.now().strftime('%m/%d/%Y')
    
    print(f"Searching: {search_from} to {search_to}\n")
    
    # Search for AI/software keywords
    keywords = ['artificial intelligence', 'machine learning', 'software']
    
    all_opps = []
    for keyword in keywords[:1]:  # Just one keyword to avoid duplicates
        print(f"Searching for: {keyword}")
        try:
            opps = sam_client.search_by_keyword(keyword, search_from, search_to)
            all_opps.extend(opps[:20])  # Get first 20
            break
        except:
            pass
    
    print(f"\nShowing {len(all_opps)} opportunities:\n")
    print("-" * 80)
    
    # Filter for potentially relevant ones based on title/description
    ai_keywords = ['ai', 'artificial', 'intelligence', 'machine', 'learning', 
                   'data', 'analytics', 'software', 'development', 'cloud',
                   'automation', 'system', 'technology', 'digital', 'cyber']
    
    for i, opp in enumerate(all_opps, 1):
        title = opp.get('title', '').lower()
        desc = opp.get('description', '').lower()[:500]
        
        # Check if potentially relevant
        relevant = any(kw in title or kw in desc for kw in ai_keywords)
        
        print(f"\n{i}. {'⭐' if relevant else '  '} {opp.get('title', 'Unknown')[:70]}")
        print(f"     Agency: {opp.get('fullParentPathName', 'Unknown')[:60]}")
        print(f"     Type: {opp.get('type', 'Unknown')}")
        print(f"     Posted: {opp.get('postedDate', 'Unknown')}")
        print(f"     Deadline: {opp.get('responseDeadLine', 'Not specified')}")
        print(f"     Notice ID: {opp.get('noticeId', 'Unknown')}")
        
        if relevant:
            print(f"     Preview: {desc[:150]}...")
        
        print(f"     Link: {opp.get('uiLink', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("\n⭐ = Potentially relevant based on keywords")
    print("\nTo properly evaluate these with AI:")
    print("1. Fix your OpenAI API billing at https://platform.openai.com/account/billing")
    print("2. Then run: python find_rfps_now.py")

if __name__ == "__main__":
    show_rfps()