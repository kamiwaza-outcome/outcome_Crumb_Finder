#!/usr/bin/env python
"""
Run OVERKILL MODE for a specific date
Processes ALL RFPs without any filters
"""

import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading env
from enhanced_discovery import enhanced_discovery

def main():
    # For August 25th, we need to calculate days_back from today
    # Today is August 26th, so yesterday is 1 day back
    days_back = 1
    
    print("\n" + "="*70)
    print("🔥 OVERKILL MODE ACTIVATED")
    print("="*70)
    print(f"Looking back {days_back} day(s) for RFPs")
    print("Processing ALL RFPs without filters...")
    print("This will analyze EVERY single RFP from August 25th, 2024")
    print("="*70)
    
    # Run enhanced discovery in overkill mode
    enhanced_discovery(
        test_mode=False,
        overkill_mode=True,
        days_back=days_back,
        max_rfps=10000  # Set high limit for overkill mode
    )

if __name__ == "__main__":
    main()