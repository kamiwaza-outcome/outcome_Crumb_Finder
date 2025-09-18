#!/usr/bin/env python3
"""
Quick test - finds and evaluates just 3 RFPs
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sam_client import SAMClient  
from ai_qualifier import AIQualifier

def quick_test():
    print("\n🚀 QUICK RFP TEST - Finding 3 data/AI opportunities\n")
    print("=" * 60)
    
    # Initialize clients
    sam_client = SAMClient(Config.SAM_API_KEY)
    qualifier = AIQualifier(Config.OPENAI_API_KEY)
    
    # Search last 14 days
    search_from = (datetime.now() - timedelta(days=14)).strftime('%m/%d/%Y')
    search_to = datetime.now().strftime('%m/%d/%Y')
    
    print(f"Searching: {search_from} to {search_to}\n")
    
    # Search for data processing opportunities
    print("Searching for 'data processing' opportunities...")
    try:
        opportunities = sam_client.search_by_keyword('data processing', search_from, search_to)
        print(f"Found {len(opportunities)} total, evaluating first 3...\n")
        
        # Take first 3
        for i, opp in enumerate(opportunities[:3], 1):
            print(f"\n{i}. {opp.get('title', 'Unknown')[:60]}...")
            print(f"   Agency: {opp.get('fullParentPathName', 'Unknown')[:40]}")
            print(f"   Type: {opp.get('type', 'Unknown')}")
            print(f"   Posted: {opp.get('postedDate', 'Unknown')}")
            
            # Get first 200 chars of description
            desc = opp.get('description', 'No description')[:200].replace('\n', ' ')
            print(f"   About: {desc}...")
            
            print(f"\n   🤖 Evaluating with AI...")
            try:
                assessment = qualifier.assess_opportunity(opp)
                score = assessment.get('relevance_score', 0)
                qualified = assessment.get('is_qualified', False)
                
                print(f"   Score: {score}/10")
                print(f"   Qualified: {'✅ YES' if qualified else '❌ NO'}")
                print(f"   Reason: {assessment.get('justification', '')[:150]}...")
                
                if qualified:
                    print(f"   AI Application: {assessment.get('ai_application', '')[:150]}...")
                    similar = assessment.get('similar_past_rfps', [])
                    if similar:
                        print(f"   Similar to past wins: {', '.join(similar[:2])}")
                
            except Exception as e:
                print(f"   ⚠️ Evaluation error: {str(e)[:100]}")
            
            print("-" * 60)
        
        print("\n✅ Quick test complete!")
        print(f"Drive folder: https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
        print(f"Spreadsheet: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    quick_test()