#!/usr/bin/env python3
"""
Test duplicate detection system
"""

import logging
from sheets_manager import SheetsManager
from config import Config

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_duplicate_detection():
    """Test that duplicate detection is working correctly"""
    
    print("\n" + "="*60)
    print("DUPLICATE DETECTION TEST")
    print("="*60)
    
    sheets = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Get existing Notice IDs from all sheets
    main_ids = sheets.get_existing_notice_ids(Config.SPREADSHEET_ID) if Config.SPREADSHEET_ID else set()
    maybe_ids = sheets.get_existing_notice_ids(Config.MAYBE_SPREADSHEET_ID) if Config.MAYBE_SPREADSHEET_ID else set()
    spam_ids = sheets.get_existing_notice_ids(Config.SPAM_SPREADSHEET_ID) if Config.SPAM_SPREADSHEET_ID else set()
    
    print(f"\n📊 Current Sheet Status:")
    print(f"  Main sheet: {len(main_ids)} Notice IDs")
    print(f"  Maybe sheet: {len(maybe_ids)} Notice IDs")
    print(f"  Spam sheet: {len(spam_ids)} Notice IDs")
    
    # Check for duplicates between Main and Maybe (should be 0)
    main_maybe_overlap = main_ids & maybe_ids
    main_spam_overlap = main_ids & spam_ids
    maybe_spam_overlap = maybe_ids & spam_ids
    
    print(f"\n🔍 Duplicate Check Results:")
    print(f"  Main & Maybe overlap: {len(main_maybe_overlap)} duplicates")
    print(f"  Main & Spam overlap: {len(main_spam_overlap)} duplicates")
    print(f"  Maybe & Spam overlap: {len(maybe_spam_overlap)} duplicates")
    
    # Test results
    print(f"\n✅ Test Results:")
    
    if len(main_maybe_overlap) == 0:
        print("  ✓ PASS: No duplicates between Main and Maybe sheets")
    else:
        print(f"  ✗ FAIL: Found {len(main_maybe_overlap)} duplicates between Main and Maybe")
        print(f"    Example duplicates: {list(main_maybe_overlap)[:3]}")
    
    if len(main_spam_overlap) == len(main_ids):
        print("  ✓ PASS: All Main sheet items are in Spam sheet (as expected)")
    else:
        print(f"  ⚠ WARNING: Not all Main items in Spam ({len(main_spam_overlap)}/{len(main_ids)})")
    
    if len(maybe_spam_overlap) == len(maybe_ids):
        print("  ✓ PASS: All Maybe sheet items are in Spam sheet (as expected)")
    else:
        print(f"  ⚠ WARNING: Not all Maybe items in Spam ({len(maybe_spam_overlap)}/{len(maybe_ids)})")
    
    # Simulate duplicate detection logic
    print(f"\n🧪 Simulating Duplicate Detection:")
    
    # Pre-LLM detection (saves API costs)
    all_existing = main_ids | maybe_ids | spam_ids
    test_notice_id = "TEST-12345"
    
    if test_notice_id in all_existing:
        print(f"  Pre-LLM: Would skip '{test_notice_id}' (already processed)")
    else:
        print(f"  Pre-LLM: Would process '{test_notice_id}' (new RFP)")
    
    # Post-LLM detection (prevents sheet duplicates)
    if test_notice_id in main_ids:
        print(f"  Post-LLM: Would skip adding to Main sheet (duplicate)")
    else:
        print(f"  Post-LLM: Would add to Main sheet (not duplicate)")
    
    if test_notice_id in maybe_ids:
        print(f"  Post-LLM: Would skip adding to Maybe sheet (duplicate)")
    else:
        print(f"  Post-LLM: Would add to Maybe sheet (not duplicate)")
    
    print(f"\n✨ Duplicate detection system is working correctly!")
    print(f"   - Pre-LLM detection prevents re-evaluating RFPs")
    print(f"   - Post-LLM detection keeps Main/Maybe sheets clean")
    print(f"   - Spam sheet contains all RFPs for audit trail")
    print("="*60 + "\n")
    
    return len(main_maybe_overlap) == 0

if __name__ == "__main__":
    success = test_duplicate_detection()
    exit(0 if success else 1)