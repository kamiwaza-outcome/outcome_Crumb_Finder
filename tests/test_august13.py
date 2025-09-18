#!/usr/bin/env python3
"""
Test with August 13, 2025 data - direct date override
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after path setup
from enhanced_discovery import enhanced_discovery
from weekend_catchup import WeekendCatchupManager
from sam_client import SAMClient
from config import Config

# Override the get_days_to_process to return August 13
original_get_days = WeekendCatchupManager.get_days_to_process

def get_august_13(self):
    """Force August 13, 2025"""
    return ['08/13/2025']

WeekendCatchupManager.get_days_to_process = get_august_13

# Run with test mode false so it uses our override
print("\n" + "="*70)
print("🧪 Testing with Wednesday, August 13, 2025")
print("="*70)

enhanced_discovery(test_mode=False)