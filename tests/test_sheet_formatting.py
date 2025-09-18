#!/usr/bin/env python3
"""
Test the new sheet formatting features
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sheets_manager import SheetsManager
from config import Config
from datetime import datetime, timedelta

def test_sheet_formatting():
    """Test adding a sample RFP with all formatting features"""
    
    print("Testing Sheet Formatting Features...")
    print("="*50)
    
    # Initialize sheets manager
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Create test opportunity (expired)
    test_opp1 = {
        'noticeId': 'TEST_EXPIRED_001',
        'title': 'TEST - Expired RFP with High Score',
        'fullParentPathName': 'Test Agency',
        'postedDate': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
        'responseDeadLine': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
        'uiLink': 'https://sam.gov/test/expired',
        'naicsCode': '123456',
        'classificationCode': 'TEST',
        'solicitationNumber': 'TEST-001',
        'type': 'Combined Synopsis/Solicitation'
    }
    
    test_assessment1 = {
        'relevance_score': 8,
        'is_qualified': True,
        'justification': 'High score test with expired status',
        'key_requirements': ['AI', 'Machine Learning'],
        'suggested_approach': 'Test approach',
        'ai_application': 'Test AI application'
    }
    
    # Create test opportunity (active)
    test_opp2 = {
        'noticeId': 'TEST_ACTIVE_002',
        'title': 'TEST - Active RFP with Excellent Score',
        'fullParentPathName': 'Test Agency',
        'postedDate': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
        'responseDeadLine': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
        'uiLink': 'https://sam.gov/test/active',
        'naicsCode': '234567',
        'classificationCode': 'TEST',
        'solicitationNumber': 'TEST-002',
        'type': 'Sources Sought'
    }
    
    test_assessment2 = {
        'relevance_score': 9,
        'is_qualified': True,
        'justification': 'Excellent score test with active status',
        'key_requirements': ['Data Analytics', 'Cloud'],
        'suggested_approach': 'Test approach 2',
        'ai_application': 'Test AI application 2'
    }
    
    # Create test opportunity (expiring)
    test_opp3 = {
        'noticeId': 'TEST_EXPIRING_003',
        'title': 'TEST - Expiring RFP with Perfect Score',
        'fullParentPathName': 'Test Agency',
        'postedDate': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        'responseDeadLine': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
        'uiLink': 'https://sam.gov/test/expiring',
        'naicsCode': '345678',
        'classificationCode': 'TEST',
        'solicitationNumber': 'TEST-003',
        'type': 'Request for Information'
    }
    
    test_assessment3 = {
        'relevance_score': 10,
        'is_qualified': True,
        'justification': 'Perfect score test with expiring status',
        'key_requirements': ['Automation', 'Integration'],
        'suggested_approach': 'Test approach 3',
        'ai_application': 'Test AI application 3'
    }
    
    try:
        if Config.SPREADSHEET_ID:
            print("\nAdding test RFPs to main sheet...")
            
            # Add expired RFP
            sheets_manager.add_opportunity(
                Config.SPREADSHEET_ID,
                test_opp1,
                test_assessment1,
                'https://drive.google.com/test_folder1'
            )
            print(f"✅ Added expired RFP with score 8 (should show as 'High' with green background)")
            
            # Add active RFP
            sheets_manager.add_opportunity(
                Config.SPREADSHEET_ID,
                test_opp2,
                test_assessment2,
                'https://drive.google.com/test_folder2'
            )
            print(f"✅ Added active RFP with score 9 (should show as 'Excellent' with cyan background)")
            
            # Add expiring RFP
            sheets_manager.add_opportunity(
                Config.SPREADSHEET_ID,
                test_opp3,
                test_assessment3,
                'https://drive.google.com/test_folder3'
            )
            print(f"✅ Added expiring RFP with score 10 (should show as 'Perfect' with pink background)")
            
            print("\n" + "="*50)
            print("✨ Test complete! Check your main sheet for:")
            print("1. Status column showing: Expired, Active, Expiring")
            print("2. AI Score column showing: High, Excellent, Perfect")
            print("3. Colors: Red for expired (A-C), Score colors in column N")
            print("4. URLs showing full links, not 'View on SAM.gov'")
            
        else:
            print("❌ No main sheet configured")
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sheet_formatting()