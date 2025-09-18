#!/usr/bin/env python3
"""
Quick test to add a qualified RFP to the main sheet
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from config import Config
from sheets_manager import SheetsManager

def test_main_sheet():
    print("\n🔧 TESTING MAIN SHEET WRITE\n")
    print("=" * 60)
    
    sheets_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
    
    # Create a test qualified opportunity
    test_opp = {
        'title': 'Kinetic Cargo DACMS Requirement (TEST)',
        'noticeId': 'TEST-001',
        'solicitationNumber': 'W912LU25R0001',
        'fullParentPathName': 'DEPT OF DEFENSE.ARMY.LOGISTICS',
        'postedDate': '2025-08-18',
        'responseDeadLine': '2025-09-15T14:00:00-05:00',
        'naicsCode': '541512',
        'classificationCode': 'D302',
        'type': 'Solicitation',
        'uiLink': 'https://sam.gov/opp/TEST001'
    }
    
    test_assessment = {
        'is_qualified': True,
        'relevance_score': 8,
        'justification': 'This RFP for a Data Analytics and Cargo Management System aligns perfectly with Test Company capabilities in data processing, analytics, and AI orchestration.',
        'key_requirements': ['Real-time data analytics', 'Cargo tracking system', 'Predictive logistics'],
        'company_advantages': ['Distributed data processing', 'AI-powered analytics', 'Real-time insights'],
        'suggested_approach': 'Deploy Test Company platform for real-time cargo analytics with predictive capabilities',
        'ai_application': 'Use AI for predictive logistics, anomaly detection, and optimization of cargo routes'
    }
    
    print(f"Adding qualified RFP to main sheet: {Config.SPREADSHEET_ID}")
    
    try:
        # Add to main sheet
        sheets_manager.add_opportunity(
            Config.SPREADSHEET_ID,
            test_opp,
            test_assessment,
            'https://drive.google.com/drive/folders/TEST'
        )
        
        print("✅ Successfully added to main sheet!")
        print(f"\nView at: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_main_sheet()