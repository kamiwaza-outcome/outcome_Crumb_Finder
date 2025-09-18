#!/usr/bin/env python3
"""
Production-ready discovery script with dual sheet logging
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from main import RFPDiscoverySystem

def run_discovery(test_mode=False):
    print("\n" + "="*70)
    print("🚀 RFP DISCOVERY SYSTEM")
    print("="*70)
    print(f"📅 Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Main Sheet: .../{Config.SPREADSHEET_ID[-6:] if Config.SPREADSHEET_ID else 'NOT SET'}")
    print(f"📋 Spam Sheet: .../{Config.SPAM_SPREADSHEET_ID[-6:]}")
    print("="*70)
    
    try:
        # Initialize and run the system
        system = RFPDiscoverySystem()
        
        if test_mode:
            print("\n⚠️  TEST MODE - Limited search")
            # Limit searches in test mode
            Config.AI_KEYWORDS = ['artificial intelligence', 'data analytics', 'machine learning']
            Config.NAICS_CODES = Config.NAICS_CODES[:2]
        
        print("\n🔍 Starting RFP discovery...")
        print("   • Searching SAM.gov for new opportunities")
        print("   • Evaluating with AI (GPT-4o)")
        print("   • Logging ALL to spam sheet")
        print("   • Storing qualified (7+/10) to main sheet\n")
        
        results = system.run_discovery()
        
        print("\n" + "="*70)
        print("✨ DISCOVERY COMPLETE")
        print("="*70)
        print(f"\n📊 Results:")
        print(f"   • Qualified opportunities: {len(results)}")
        print(f"   • Check spam sheet for ALL evaluated RFPs with scores")
        
        print(f"\n📋 View Results:")
        print(f"   • ALL RFPs (with scores 1-10):")
        print(f"     https://docs.google.com/spreadsheets/d/{Config.SPAM_SPREADSHEET_ID}")
        
        if Config.SPREADSHEET_ID:
            print(f"\n   • QUALIFIED RFPs (7+/10 only):")
            print(f"     https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
        
        if Config.GOOGLE_DRIVE_FOLDER_ID:
            print(f"\n   • Assessment Reports:")
            print(f"     https://drive.google.com/drive/folders/{Config.GOOGLE_DRIVE_FOLDER_ID}")
        
        print("\n💡 The spam sheet shows EVERY evaluated RFP with its AI score.")
        print("   Sort by the 'AI Score' column to see highest scoring opportunities.\n")
        
        return results
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nPlease check:")
        print("  1. API keys are set in .env")
        print("  2. Service account has access to both sheets")
        print("  3. Network connection is working")
        return []

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run RFP Discovery System')
    parser.add_argument('--test', action='store_true', help='Run in test mode with limited searches')
    
    args = parser.parse_args()
    
    run_discovery(test_mode=args.test)