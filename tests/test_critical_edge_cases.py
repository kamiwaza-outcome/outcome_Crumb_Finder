#!/usr/bin/env python3
"""
Critical Edge Case Testing for RFP Discovery System

Tests the most critical failure modes that could cause data loss, 
security breaches, or system unavailability.
"""

import json
import logging
import traceback
from datetime import datetime
from unittest.mock import patch, MagicMock
import requests

# Import system components
from config import Config
from sam_client import SAMClient
from ai_qualifier import AIQualifier
from sheets_manager import SheetsManager
from drive_manager import DriveManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_critical_failure_modes():
    """Test the most critical failure modes"""
    results = []
    
    print("CRITICAL EDGE CASE TESTING")
    print("="*50)
    
    # 1. Test what happens when all APIs are down
    print("\n1. Testing complete API outage scenario...")
    with patch('requests.Session.get') as mock_get, \
         patch('openai.OpenAI') as mock_openai, \
         patch('googleapiclient.discovery.build') as mock_google:
        
        mock_get.side_effect = requests.exceptions.ConnectionError("All APIs down")
        mock_openai.side_effect = Exception("OpenAI unavailable")
        mock_google.side_effect = Exception("Google APIs unavailable")
        
        try:
            # Try to run a discovery process
            if Config.SAM_API_KEY:
                client = SAMClient(Config.SAM_API_KEY)
                opportunities = client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                
                if opportunities:
                    results.append({
                        'severity': 'CRITICAL',
                        'issue': 'SYSTEM_CONTINUES_WITH_APIS_DOWN',
                        'description': 'System returned data when all APIs should be down',
                        'impact': 'Could provide stale or incorrect data'
                    })
                    print("❌ CRITICAL: System continues operating when APIs are down")
                else:
                    print("✓ System correctly handles API outage")
                    
        except Exception as e:
            print(f"✓ System correctly fails when APIs are down: {str(e)[:100]}")
    
    # 2. Test malformed credential files
    print("\n2. Testing malformed credential handling...")
    try:
        # Create a temporary malformed JSON file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": "json", "missing_key"}')  # Malformed JSON
            temp_path = f.name
        
        try:
            manager = SheetsManager(temp_path)
            results.append({
                'severity': 'HIGH',
                'issue': 'MALFORMED_CREDENTIALS_ACCEPTED',
                'description': 'System accepted malformed credentials file',
                'impact': 'Could lead to runtime failures'
            })
            print("❌ HIGH: System accepted malformed credentials")
        except Exception as e:
            print(f"✓ System correctly rejected malformed credentials: {str(e)[:100]}")
        
        # Cleanup
        import os
        os.unlink(temp_path)
        
    except Exception as e:
        print(f"Credential test failed: {str(e)}")
    
    # 3. Test extremely large RFP data handling
    print("\n3. Testing large data handling...")
    try:
        # Create massive RFP data
        massive_rfp = {
            "title": "Large RFP " + "X" * 50000,  # 50KB title
            "description": "Description " + "Y" * 500000,  # 500KB description
            "noticeId": "test_massive",
            "fullParentPathName": "Agency " + "Z" * 10000
        }
        
        if Config.OPENAI_API_KEY:
            qualifier = AIQualifier(Config.OPENAI_API_KEY)
            start_time = datetime.now()
            
            try:
                result = qualifier.assess_opportunity(massive_rfp)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                if duration > 120:  # More than 2 minutes
                    results.append({
                        'severity': 'MEDIUM',
                        'issue': 'LARGE_DATA_TIMEOUT',
                        'description': f'Large RFP processing took {duration:.1f} seconds',
                        'impact': 'Could cause timeouts and delays'
                    })
                    print(f"⚠️  Large RFP took {duration:.1f} seconds to process")
                else:
                    print(f"✓ Large RFP processed in {duration:.1f} seconds")
                    
            except Exception as e:
                if "token" in str(e).lower() or "length" in str(e).lower():
                    print(f"✓ System correctly handled oversized input: {str(e)[:100]}")
                else:
                    results.append({
                        'severity': 'HIGH',
                        'issue': 'LARGE_DATA_CRASH',
                        'description': f'System crashed on large data: {str(e)[:200]}',
                        'impact': 'System fails on large RFPs'
                    })
                    print(f"❌ HIGH: System crashed on large data: {str(e)[:100]}")
    
    except Exception as e:
        print(f"Large data test failed: {str(e)}")
    
    # 4. Test concurrent access to Google Sheets
    print("\n4. Testing concurrent sheet operations...")
    try:
        import threading
        import time
        
        errors = []
        successes = []
        
        def concurrent_write(thread_id):
            try:
                if Config.GOOGLE_SHEETS_CREDS_PATH and Config.SPAM_SPREADSHEET_ID:
                    manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                    
                    test_rfp = {
                        "title": f"Concurrent Test {thread_id}",
                        "noticeId": f"concurrent_{thread_id}_{int(time.time())}",
                        "fullParentPathName": "Test Agency"
                    }
                    
                    test_assessment = {
                        "relevance_score": 5,
                        "is_qualified": False,
                        "justification": f"Concurrent test {thread_id}"
                    }
                    
                    manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, test_rfp, test_assessment)
                    successes.append(thread_id)
                    
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Launch 5 concurrent writes
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_write, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)
        
        if len(errors) > 2:  # More than 2 failures out of 5
            results.append({
                'severity': 'MEDIUM',
                'issue': 'CONCURRENT_ACCESS_FAILURES',
                'description': f'{len(errors)} out of 5 concurrent operations failed',
                'impact': 'System may lose data under load'
            })
            print(f"⚠️  {len(errors)}/5 concurrent operations failed")
        else:
            print(f"✓ Concurrent operations: {len(successes)}/5 succeeded, {len(errors)}/5 failed")
        
        # Print error details
        for thread_id, error in errors[:3]:  # Show first 3 errors
            print(f"   Thread {thread_id} error: {error[:100]}")
    
    except Exception as e:
        print(f"Concurrent test failed: {str(e)}")
    
    # 5. Test invalid date formats
    print("\n5. Testing invalid date handling...")
    try:
        if Config.SAM_API_KEY:
            client = SAMClient(Config.SAM_API_KEY)
            
            invalid_dates = [
                ("invalid_date", "01/01/2024"),
                ("01/01/2024", "invalid_date"),
                ("13/40/2024", "01/01/2024"),  # Invalid month/day
                ("01/01/1900", "01/01/1901"),  # Very old dates
                ("01/01/2050", "01/01/2051"),  # Future dates
                ("", ""),  # Empty dates
            ]
            
            for start_date, end_date in invalid_dates:
                try:
                    opportunities = client.search_by_naics("541511", start_date, end_date)
                    if opportunities:
                        results.append({
                            'severity': 'LOW',
                            'issue': 'INVALID_DATE_ACCEPTED',
                            'description': f'System accepted invalid dates: {start_date} to {end_date}',
                            'impact': 'Could return incorrect data'
                        })
                        print(f"⚠️  Invalid dates accepted: {start_date} to {end_date}")
                except Exception as e:
                    print(f"✓ Correctly rejected invalid dates {start_date} to {end_date}: {str(e)[:50]}")
    
    except Exception as e:
        print(f"Date validation test failed: {str(e)}")
    
    # 6. Test what happens with corrupted opportunity data
    print("\n6. Testing corrupted opportunity data...")
    try:
        corrupted_opportunities = [
            None,  # None object
            {},    # Empty dict
            {"title": None, "description": None, "noticeId": None},  # All None
            {"title": "", "description": "", "noticeId": ""},  # All empty strings
            {"malformed": "data", "no_standard_fields": True},  # Wrong structure
            {"title": {"nested": "object"}, "noticeId": "test"},  # Nested objects
        ]
        
        for i, opp in enumerate(corrupted_opportunities):
            try:
                if Config.OPENAI_API_KEY:
                    qualifier = AIQualifier(Config.OPENAI_API_KEY)
                    result = qualifier.assess_opportunity(opp)
                    
                    # Check if it handled gracefully
                    if result.get('error'):
                        print(f"✓ Correctly handled corrupted data {i}: {result.get('justification', '')[:50]}")
                    else:
                        score = result.get('relevance_score', 0)
                        if score > 0:
                            results.append({
                                'severity': 'MEDIUM',
                                'issue': 'CORRUPTED_DATA_SCORED',
                                'description': f'Corrupted data received score {score}: {str(opp)[:100]}',
                                'impact': 'Could generate false positives'
                            })
                            print(f"⚠️  Corrupted data got score {score}: {str(opp)[:50]}")
                        else:
                            print(f"✓ Corrupted data correctly scored 0: {str(opp)[:50]}")
            
            except Exception as e:
                print(f"✓ Correctly failed on corrupted data {i}: {str(e)[:50]}")
    
    except Exception as e:
        print(f"Corrupted data test failed: {str(e)}")
    
    # 7. Test missing environment variables
    print("\n7. Testing missing environment variables...")
    critical_vars = ['SAM_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_SHEETS_CREDS_PATH']
    
    for var in critical_vars:
        current_value = getattr(Config, var, None)
        if not current_value:
            results.append({
                'severity': 'CRITICAL',
                'issue': f'MISSING_{var}',
                'description': f'{var} is not configured',
                'impact': 'Core functionality unavailable'
            })
            print(f"❌ CRITICAL: {var} not configured")
        else:
            print(f"✓ {var} is configured")
    
    # Generate summary
    print(f"\n" + "="*50)
    print("CRITICAL EDGE CASE TEST SUMMARY")
    print("="*50)
    
    critical_count = sum(1 for r in results if r['severity'] == 'CRITICAL')
    high_count = sum(1 for r in results if r['severity'] == 'HIGH')
    medium_count = sum(1 for r in results if r['severity'] == 'MEDIUM')
    low_count = sum(1 for r in results if r['severity'] == 'LOW')
    
    print(f"Total Issues: {len(results)}")
    print(f"Critical: {critical_count}")
    print(f"High: {high_count}")
    print(f"Medium: {medium_count}")
    print(f"Low: {low_count}")
    
    if critical_count > 0:
        print(f"\n🚨 CRITICAL ISSUES:")
        for result in results:
            if result['severity'] == 'CRITICAL':
                print(f"  - {result['issue']}: {result['description']}")
    
    # Save detailed results
    report = {
        'timestamp': datetime.now().isoformat(),
        'test_type': 'critical_edge_cases',
        'total_issues': len(results),
        'summary': {
            'critical': critical_count,
            'high': high_count,
            'medium': medium_count,
            'low': low_count
        },
        'issues': results
    }
    
    filename = f"critical_edge_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {filename}")
    
    return results

if __name__ == "__main__":
    test_critical_failure_modes()