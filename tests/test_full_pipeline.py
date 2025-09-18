#!/usr/bin/env python3
"""
Test the full pipeline with August 13, 2025 data
Shows: Filtering -> GPT-5-mini screening -> GPT-5 deep analysis -> Sheet distribution
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_discovery import enhanced_discovery
from weekend_catchup import WeekendCatchupManager

# Override to use August 13
def get_august_13(self):
    return ['08/13/2025']

WeekendCatchupManager.get_days_to_process = get_august_13

print("\n" + "="*70)
print("🚀 FULL PIPELINE TEST - August 13, 2025")
print("="*70)
print("\nExpected flow:")
print("1. Cast wide net with filters (~500 target)")
print("2. GPT-5-mini screens with FULL descriptions (score 1-10)")
print("3. Score 4+ go to GPT-5 for deep analysis")
print("4. Results distributed:")
print("   • Qualified (7-10 from GPT-5) → Main sheet + Drive")
print("   • Maybe (4-6 from GPT-5) → Maybe sheet")
print("   • ALL RFPs → Spam sheet")
print("="*70)

# Run the full pipeline
results = enhanced_discovery(test_mode=False)