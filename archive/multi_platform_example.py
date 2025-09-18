#!/usr/bin/env python3
"""
Example of how to handle multiple RFP platforms with duplicate detection
"""

def create_universal_id(platform: str, platform_id: str) -> str:
    """Create a universal ID that includes platform prefix"""
    # Format: PLATFORM:ID
    return f"{platform}:{platform_id}"

def detect_cross_platform_duplicates(rfp_data: dict) -> str:
    """Generate a content hash for cross-platform duplicate detection"""
    import hashlib
    
    # Create a fingerprint based on key fields that would be same across platforms
    fingerprint = f"{rfp_data.get('title', '').lower().strip()[:100]}"
    fingerprint += f"{rfp_data.get('agency', '').lower().strip()}"
    fingerprint += f"{rfp_data.get('posted_date', '')[:10]}"  # Date only
    
    # Generate hash of the fingerprint
    return hashlib.md5(fingerprint.encode()).hexdigest()[:12]

# Example usage:
sam_rfp = {
    'platform': 'SAM',
    'noticeId': 'abc123',
    'title': 'AI Development Services',
    'agency': 'Department of Defense'
}

sibr_rfp = {
    'platform': 'SIBR',
    'rfp_id': 'XYZ-789',  # Different ID field name
    'title': 'AI Development Services',  # Same RFP!
    'agency': 'Department of Defense'
}

vulcan_rfp = {
    'platform': 'VULCAN',
    'opp_number': 'VUL-456',
    'title': 'Machine Learning Platform',
    'agency': 'NASA'
}

# Platform-specific IDs (for exact duplicates on same platform)
sam_universal_id = create_universal_id('SAM', sam_rfp['noticeId'])
sibr_universal_id = create_universal_id('SIBR', sibr_rfp['rfp_id'])
vulcan_universal_id = create_universal_id('VULCAN', vulcan_rfp['opp_number'])

print("Platform-Specific IDs:")
print(f"  SAM: {sam_universal_id}")
print(f"  SIBR: {sibr_universal_id}")
print(f"  Vulcan: {vulcan_universal_id}")

# Content hashes (for cross-platform duplicates)
sam_hash = detect_cross_platform_duplicates(sam_rfp)
sibr_hash = detect_cross_platform_duplicates(sibr_rfp)
vulcan_hash = detect_cross_platform_duplicates(vulcan_rfp)

print("\nContent Hashes:")
print(f"  SAM RFP: {sam_hash}")
print(f"  SIBR RFP: {sibr_hash}")  # Should match SAM!
print(f"  Vulcan RFP: {vulcan_hash}")

if sam_hash == sibr_hash:
    print("\n⚠️ Detected: SAM and SIBR have the same RFP (cross-platform duplicate)")

# In sheets_manager.py, you'd track both:
class EnhancedDuplicateDetection:
    def __init__(self):
        self.platform_ids = set()  # Platform-specific IDs
        self.content_hashes = set()  # Cross-platform detection
    
    def is_duplicate(self, platform: str, platform_id: str, rfp_data: dict) -> tuple:
        universal_id = f"{platform}:{platform_id}"
        content_hash = detect_cross_platform_duplicates(rfp_data)
        
        # Check both types of duplicates
        platform_duplicate = universal_id in self.platform_ids
        content_duplicate = content_hash in self.content_hashes
        
        return platform_duplicate, content_duplicate
    
    def add_rfp(self, platform: str, platform_id: str, rfp_data: dict):
        universal_id = f"{platform}:{platform_id}"
        content_hash = detect_cross_platform_duplicates(rfp_data)
        
        self.platform_ids.add(universal_id)
        self.content_hashes.add(content_hash)