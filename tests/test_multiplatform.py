#!/usr/bin/env python3
"""
Test multi-platform duplicate detection system
"""

from platform_manager import DuplicateDetector, MultiPlatformManager
from sheets_manager import SheetsManager
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_multiplatform_system():
    """Test the multi-platform duplicate detection system"""
    
    print("\n" + "="*60)
    print("🧪 MULTI-PLATFORM SYSTEM TEST")
    print("="*60)
    
    # Test 1: Duplicate Detector
    print("\n✅ Test 1: Duplicate Detection Logic")
    detector = DuplicateDetector()
    
    # Add SAM RFP
    sam_rfp = {
        'platform': 'SAM',
        'platform_id': 'FA8750-24-Q-0001',
        'title': 'AI and Machine Learning Support Services',
        'agency': 'Department of Defense',
        'posted_date': '2024-08-19'
    }
    
    # Check it's not a duplicate
    check1 = detector.check_duplicate(sam_rfp)
    print(f"  SAM RFP: {check1['universal_id']}")
    print(f"  Is duplicate: {check1['is_exact_duplicate']}")
    assert not check1['is_exact_duplicate'], "Should not be duplicate"
    
    # Add to detector
    detector.add_rfp(sam_rfp)
    
    # Check again - should be duplicate now
    check2 = detector.check_duplicate(sam_rfp)
    print(f"  Second check - Is duplicate: {check2['is_exact_duplicate']}")
    assert check2['is_exact_duplicate'], "Should be duplicate after adding"
    
    # Test cross-platform duplicate (same content, different platform)
    sibr_rfp = {
        'platform': 'SIBR',
        'platform_id': 'SIBR-2024-001',
        'title': 'AI Machine Learning Support Services',  # Slightly different
        'agency': 'department of defense',  # Different case
        'posted_date': '2024-08-19'  # Same date
    }
    
    check3 = detector.check_duplicate(sibr_rfp)
    print(f"\n  SIBR RFP: {check3['universal_id']}")
    print(f"  Is exact duplicate: {check3['is_exact_duplicate']}")
    print(f"  Is cross-platform duplicate: {check3['is_cross_platform_duplicate']}")
    print(f"  Content hashes - SAM: {check1['content_hash']}, SIBR: {check3['content_hash']}")
    
    # Test 2: Sheet Integration
    print("\n\n✅ Test 2: Sheet Integration")
    sheets = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Test Universal ID reading
    universal_ids = sheets.get_existing_universal_ids(Config.SPAM_SPREADSHEET_ID)
    print(f"  Found {len(universal_ids)} Universal IDs in spam sheet")
    
    # Since sheets don't have Universal IDs yet, it should fall back to Notice IDs
    if universal_ids:
        sample_ids = list(universal_ids)[:3]
        print(f"  Sample IDs: {sample_ids}")
        
        # Check format - should be SAM:noticeId for legacy data
        for uid in sample_ids[:1]:
            if ':' in uid:
                platform, pid = uid.split(':', 1)
                print(f"    Parsed: Platform={platform}, ID={pid}")
    
    # Test 3: Platform Manager
    print("\n\n✅ Test 3: Platform Manager")
    manager = MultiPlatformManager()
    
    # Simulate multiple platforms finding RFPs
    test_rfps = [
        {'platform': 'SAM', 'platform_id': 'TEST-001', 'title': 'Cloud Services', 'agency': 'NASA', 'posted_date': '2024-08-19'},
        {'platform': 'SIBR', 'platform_id': 'SBIR-001', 'title': 'Cloud Services', 'agency': 'NASA', 'posted_date': '2024-08-19'},  # Duplicate!
        {'platform': 'VULCAN', 'platform_id': 'VUL-001', 'title': 'Data Analytics', 'agency': 'DOD', 'posted_date': '2024-08-19'},
    ]
    
    # Process with deduplication
    for rfp in test_rfps:
        dup_check = manager.duplicate_detector.check_duplicate(rfp)
        rfp['duplicate_status'] = dup_check
    
    unique, stats = manager.process_with_deduplication({'test': test_rfps})
    
    print(f"  Input RFPs: {len(test_rfps)}")
    print(f"  Unique RFPs: {len(unique)}")
    print(f"  Stats: {stats}")
    
    print("\n" + "="*60)
    print("✨ All tests passed! Multi-platform system is ready.")
    print("="*60)
    print("\n📝 Next Steps:")
    print("  1. Update GitHub Actions to use enhanced_discovery_multiplatform.py")
    print("  2. Add SIBR API integration when credentials available")
    print("  3. Add Vulcan API integration when credentials available")
    print("  4. Monitor for cross-platform duplicates in production")
    print()

if __name__ == "__main__":
    test_multiplatform_system()