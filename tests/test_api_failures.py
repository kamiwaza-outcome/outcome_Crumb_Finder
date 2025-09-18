#!/usr/bin/env python3
"""
Comprehensive API failure and edge case testing for RFP Discovery System

This script tests various failure modes and edge cases for all API integrations:
- SAM.gov API: rate limits, malformed data, network timeouts
- OpenAI API (GPT-5 and GPT-5-mini): timeouts, token limits, empty responses
- Google Sheets API: permission issues, quota limits, concurrent writes
- Google Drive API: upload failures, folder creation issues

The script simulates real-world failure scenarios to identify vulnerabilities
and test the robustness of error handling.
"""

import json
import time
import random
import logging
import threading
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import patch, MagicMock
import requests
import openai

# Import system components
from config import Config
from sam_client import SAMClient
from ai_qualifier import AIQualifier
from sheets_manager import SheetsManager
from drive_manager import DriveManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_failure_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APIFailureTester:
    """Comprehensive API failure testing framework"""
    
    def __init__(self):
        self.test_results = []
        self.vulnerability_report = {
            'critical_vulnerabilities': [],
            'high_risk_issues': [],
            'medium_risk_issues': [],
            'low_risk_issues': [],
            'recommendations': []
        }
        
    def run_all_tests(self):
        """Execute comprehensive API failure test suite"""
        logger.info("Starting comprehensive API failure testing...")
        
        test_methods = [
            self.test_sam_api_failures,
            self.test_openai_api_failures,
            self.test_google_sheets_failures,
            self.test_google_drive_failures,
            self.test_network_failures,
            self.test_credential_failures,
            self.test_concurrent_operations,
            self.test_data_corruption_scenarios
        ]
        
        for test_method in test_methods:
            try:
                logger.info(f"Running {test_method.__name__}...")
                test_method()
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed: {str(e)}")
                self.add_result("SYSTEM_ERROR", test_method.__name__, f"Test framework failure: {str(e)}")
        
        self.generate_vulnerability_report()
        return self.vulnerability_report
    
    def add_result(self, severity: str, test_name: str, description: str, impact: str = "", recommendation: str = ""):
        """Add test result to vulnerability tracking"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'test_name': test_name,
            'description': description,
            'impact': impact,
            'recommendation': recommendation
        }
        self.test_results.append(result)
        
        # Categorize by severity
        if severity == "CRITICAL":
            self.vulnerability_report['critical_vulnerabilities'].append(result)
        elif severity == "HIGH":
            self.vulnerability_report['high_risk_issues'].append(result)
        elif severity == "MEDIUM":
            self.vulnerability_report['medium_risk_issues'].append(result)
        elif severity == "LOW":
            self.vulnerability_report['low_risk_issues'].append(result)

    def test_sam_api_failures(self):
        """Test SAM.gov API failure scenarios"""
        logger.info("Testing SAM.gov API failure modes...")
        
        # Test with invalid API key
        self._test_sam_invalid_credentials()
        
        # Test rate limiting simulation
        self._test_sam_rate_limiting()
        
        # Test malformed responses
        self._test_sam_malformed_responses()
        
        # Test network timeouts
        self._test_sam_network_timeouts()
        
        # Test empty/null responses
        self._test_sam_empty_responses()
        
        # Test large dataset handling
        self._test_sam_large_datasets()

    def _test_sam_invalid_credentials(self):
        """Test SAM API behavior with invalid credentials"""
        try:
            fake_client = SAMClient("invalid_api_key_123")
            
            # This should fail gracefully
            opportunities = fake_client.search_by_naics("541511", "01/01/2024", "01/02/2024")
            
            if opportunities:
                self.add_result(
                    "HIGH", 
                    "SAM_INVALID_CREDENTIALS",
                    "SAM API returned data with invalid credentials",
                    "System may be using cached data or bypassing authentication",
                    "Verify API key validation and error handling"
                )
        except Exception as e:
            if "unauthorized" in str(e).lower() or "403" in str(e) or "401" in str(e):
                logger.info("✓ SAM API correctly rejects invalid credentials")
            else:
                self.add_result(
                    "MEDIUM",
                    "SAM_CREDENTIAL_ERROR_HANDLING",
                    f"Unexpected error with invalid credentials: {str(e)}",
                    "Poor error message may confuse users",
                    "Improve credential validation error messages"
                )

    def _test_sam_rate_limiting(self):
        """Test SAM API rate limiting behavior"""
        if not Config.SAM_API_KEY:
            self.add_result("CRITICAL", "SAM_NO_API_KEY", "SAM API key not configured", 
                          "System cannot function", "Configure SAM_API_KEY")
            return
            
        try:
            client = SAMClient(Config.SAM_API_KEY)
            
            # Rapid-fire requests to trigger rate limiting
            requests_made = 0
            rate_limited = False
            
            for i in range(10):  # Make multiple rapid requests
                try:
                    client.search_by_keyword("software", "01/01/2024", "01/02/2024")
                    requests_made += 1
                    time.sleep(0.1)  # Very short delay
                except Exception as e:
                    if "429" in str(e) or "rate" in str(e).lower():
                        rate_limited = True
                        logger.info(f"✓ Rate limiting triggered after {requests_made} requests")
                        break
                    else:
                        logger.warning(f"Unexpected error during rate limit test: {str(e)}")
            
            if not rate_limited and requests_made >= 5:
                self.add_result(
                    "LOW",
                    "SAM_NO_RATE_LIMITING_OBSERVED",
                    "No rate limiting observed in rapid requests",
                    "System may hit rate limits unexpectedly in production",
                    "Implement request throttling and retry logic"
                )
        except Exception as e:
            logger.error(f"Rate limiting test failed: {str(e)}")

    def _test_sam_malformed_responses(self):
        """Test handling of malformed SAM API responses"""
        # Use mock to simulate malformed responses
        with patch('sam_client.SAMClient._make_request') as mock_request:
            client = SAMClient(Config.SAM_API_KEY or "test_key")
            
            # Test malformed JSON
            mock_request.return_value = {"malformed": "no_opportunities_data"}
            try:
                result = client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                if not result:  # Should handle gracefully
                    logger.info("✓ Handled malformed JSON response correctly")
                else:
                    self.add_result(
                        "MEDIUM",
                        "SAM_MALFORMED_JSON_HANDLING",
                        "System returned data from malformed response",
                        "May cause data corruption or application crashes",
                        "Add strict response validation"
                    )
            except Exception as e:
                if "key" in str(e).lower():  # KeyError expected
                    logger.info("✓ Correctly failed on malformed JSON")
                else:
                    self.add_result(
                        "HIGH",
                        "SAM_MALFORMED_JSON_ERROR",
                        f"Unexpected error with malformed JSON: {str(e)}",
                        "System may crash on malformed responses",
                        "Implement robust JSON validation"
                    )
            
            # Test empty response
            mock_request.return_value = {}
            try:
                result = client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                logger.info("✓ Handled empty response correctly")
            except Exception as e:
                self.add_result(
                    "MEDIUM",
                    "SAM_EMPTY_RESPONSE_ERROR",
                    f"System failed on empty response: {str(e)}",
                    "System may crash on empty API responses",
                    "Add null/empty response handling"
                )

    def _test_sam_network_timeouts(self):
        """Test SAM API network timeout handling"""
        if not Config.SAM_API_KEY:
            return
            
        # Simulate slow network by using very short timeout
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
            
            client = SAMClient(Config.SAM_API_KEY)
            try:
                result = client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                if not result:
                    logger.info("✓ Handled network timeout correctly")
                else:
                    self.add_result(
                        "HIGH",
                        "SAM_TIMEOUT_NOT_HANDLED",
                        "System returned data despite timeout",
                        "May cause unpredictable behavior",
                        "Ensure timeout exceptions are properly caught"
                    )
            except Exception as e:
                if "timeout" in str(e).lower():
                    logger.info("✓ Correctly propagated timeout error")
                else:
                    self.add_result(
                        "MEDIUM",
                        "SAM_TIMEOUT_ERROR_HANDLING",
                        f"Unexpected timeout error: {str(e)}",
                        "Poor timeout error handling",
                        "Improve timeout error messages"
                    )

    def _test_sam_empty_responses(self):
        """Test handling of empty/null SAM responses"""
        with patch('sam_client.SAMClient._make_request') as mock_request:
            client = SAMClient(Config.SAM_API_KEY or "test_key")
            
            # Test null opportunities data
            mock_request.return_value = {"opportunitiesData": None, "totalRecords": 0}
            try:
                result = client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                if result == [] or result is None:
                    logger.info("✓ Handled null opportunities data correctly")
                else:
                    self.add_result(
                        "MEDIUM",
                        "SAM_NULL_DATA_HANDLING",
                        "System didn't handle null opportunities data properly",
                        "May cause NoneType iteration errors",
                        "Add null data validation"
                    )
            except Exception as e:
                self.add_result(
                    "HIGH",
                    "SAM_NULL_DATA_ERROR",
                    f"System crashed on null data: {str(e)}",
                    "Application crashes on null API responses",
                    "Add defensive null checking"
                )

    def _test_sam_large_datasets(self):
        """Test SAM API with large datasets"""
        # This is more of a stress test
        if not Config.SAM_API_KEY:
            return
            
        try:
            client = SAMClient(Config.SAM_API_KEY)
            start_time = time.time()
            
            # Try to get a large number of results
            opportunities = client.search_by_keyword("software", "01/01/2024", "12/31/2024")
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 120:  # More than 2 minutes
                self.add_result(
                    "LOW",
                    "SAM_SLOW_LARGE_DATASETS",
                    f"Large dataset query took {duration:.1f} seconds",
                    "System may timeout on large datasets",
                    "Implement pagination and progress indicators"
                )
            
            if len(opportunities) > 1000:
                logger.info(f"✓ Successfully handled {len(opportunities)} opportunities")
            
        except Exception as e:
            self.add_result(
                "MEDIUM",
                "SAM_LARGE_DATASET_ERROR",
                f"Failed to handle large dataset: {str(e)}",
                "System may fail on large data volumes",
                "Implement chunking and memory management"
            )

    def test_openai_api_failures(self):
        """Test OpenAI API failure scenarios"""
        logger.info("Testing OpenAI API failure modes...")
        
        # Test with invalid API key
        self._test_openai_invalid_credentials()
        
        # Test token limit scenarios
        self._test_openai_token_limits()
        
        # Test timeout scenarios
        self._test_openai_timeouts()
        
        # Test empty responses
        self._test_openai_empty_responses()
        
        # Test malformed prompts
        self._test_openai_malformed_prompts()
        
        # Test model availability
        self._test_openai_model_availability()

    def _test_openai_invalid_credentials(self):
        """Test OpenAI API with invalid credentials"""
        try:
            fake_qualifier = AIQualifier("invalid_api_key_123")
            
            test_opportunity = {
                "title": "AI Software Development",
                "description": "Test opportunity",
                "noticeId": "test_123"
            }
            
            result = fake_qualifier.assess_opportunity(test_opportunity)
            
            if result.get('error'):
                logger.info("✓ OpenAI correctly handled invalid credentials")
            else:
                self.add_result(
                    "HIGH",
                    "OPENAI_INVALID_CREDENTIALS",
                    "OpenAI returned assessment with invalid credentials",
                    "System may be using cached data or bypassing authentication",
                    "Verify OpenAI API key validation"
                )
        except Exception as e:
            if "unauthorized" in str(e).lower() or "401" in str(e):
                logger.info("✓ OpenAI correctly rejects invalid credentials")
            else:
                self.add_result(
                    "MEDIUM",
                    "OPENAI_CREDENTIAL_ERROR_HANDLING",
                    f"Unexpected error with invalid OpenAI credentials: {str(e)}",
                    "Poor error handling may confuse users",
                    "Improve OpenAI credential validation messages"
                )

    def _test_openai_token_limits(self):
        """Test OpenAI token limit handling"""
        if not Config.OPENAI_API_KEY:
            self.add_result("CRITICAL", "OPENAI_NO_API_KEY", "OpenAI API key not configured",
                          "Core AI functionality unavailable", "Configure OPENAI_API_KEY")
            return
        
        try:
            qualifier = AIQualifier(Config.OPENAI_API_KEY)
            
            # Create extremely long description to trigger token limits
            huge_description = "This is a test description. " * 10000  # ~50,000 tokens
            
            test_opportunity = {
                "title": "AI Software Development",
                "description": huge_description,
                "noticeId": "test_token_limit",
                "fullParentPathName": "Test Agency",
                "responseDeadLine": "2024-12-31"
            }
            
            result = qualifier.assess_opportunity(test_opportunity)
            
            if result.get('error'):
                if "token" in result.get('justification', '').lower():
                    logger.info("✓ Correctly handled token limit error")
                else:
                    self.add_result(
                        "MEDIUM",
                        "OPENAI_TOKEN_LIMIT_UNCLEAR",
                        "Token limit error but unclear error message",
                        "Users won't understand why assessment failed",
                        "Improve token limit error messages"
                    )
            else:
                # Check if description was truncated
                if len(result.get('justification', '')) < 50:
                    self.add_result(
                        "HIGH",
                        "OPENAI_TOKEN_LIMIT_SILENT_TRUNCATION",
                        "Large input was silently truncated without warning",
                        "Users won't know their data was incomplete",
                        "Add warnings for truncated input"
                    )
                else:
                    logger.info("✓ Successfully handled large input")
                    
        except Exception as e:
            self.add_result(
                "HIGH",
                "OPENAI_TOKEN_LIMIT_ERROR",
                f"System crashed on token limit: {str(e)}",
                "Application fails on large RFP descriptions",
                "Implement input truncation with warnings"
            )

    def _test_openai_timeouts(self):
        """Test OpenAI timeout handling"""
        if not Config.OPENAI_API_KEY:
            return
            
        # Mock timeout scenario
        with patch('openai.OpenAI.chat.completions.create') as mock_create:
            mock_create.side_effect = openai.APITimeoutError("Request timed out")
            
            qualifier = AIQualifier(Config.OPENAI_API_KEY)
            test_opportunity = {
                "title": "Test Opportunity",
                "description": "Test description",
                "noticeId": "test_timeout"
            }
            
            try:
                result = qualifier.assess_opportunity(test_opportunity)
                
                if result.get('error'):
                    logger.info("✓ Correctly handled OpenAI timeout")
                else:
                    self.add_result(
                        "HIGH",
                        "OPENAI_TIMEOUT_NOT_HANDLED",
                        "System returned assessment despite timeout",
                        "May return stale or incorrect data",
                        "Ensure timeout exceptions are properly handled"
                    )
            except Exception as e:
                if "timeout" in str(e).lower():
                    logger.info("✓ Correctly propagated timeout error")
                else:
                    self.add_result(
                        "MEDIUM",
                        "OPENAI_TIMEOUT_ERROR_HANDLING",
                        f"Unexpected timeout error: {str(e)}",
                        "Poor timeout error handling",
                        "Improve timeout error messages and retry logic"
                    )

    def _test_openai_empty_responses(self):
        """Test OpenAI empty response handling"""
        if not Config.OPENAI_API_KEY:
            return
            
        # Mock empty response
        with patch('openai.OpenAI.chat.completions.create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = ""  # Empty content
            mock_create.return_value = mock_response
            
            qualifier = AIQualifier(Config.OPENAI_API_KEY)
            test_opportunity = {
                "title": "Test Opportunity",
                "description": "Test description",
                "noticeId": "test_empty"
            }
            
            try:
                result = qualifier.assess_opportunity(test_opportunity)
                
                if result.get('error') and 'empty' in result.get('justification', '').lower():
                    logger.info("✓ Correctly handled empty OpenAI response")
                else:
                    self.add_result(
                        "MEDIUM",
                        "OPENAI_EMPTY_RESPONSE_HANDLING",
                        "System didn't properly handle empty OpenAI response",
                        "May cause assessment failures or incorrect scores",
                        "Add empty response detection and retry logic"
                    )
            except Exception as e:
                self.add_result(
                    "HIGH",
                    "OPENAI_EMPTY_RESPONSE_ERROR",
                    f"System crashed on empty response: {str(e)}",
                    "Application crashes on empty AI responses",
                    "Add defensive empty response handling"
                )

    def _test_openai_malformed_prompts(self):
        """Test OpenAI with malformed or unusual prompts"""
        if not Config.OPENAI_API_KEY:
            return
            
        qualifier = AIQualifier(Config.OPENAI_API_KEY)
        
        # Test with null/missing fields
        malformed_opportunities = [
            {"title": None, "description": None, "noticeId": "test_null"},
            {"noticeId": "test_minimal"},  # Missing most fields
            {"title": "", "description": "", "noticeId": "test_empty"},  # Empty strings
        ]
        
        for opp in malformed_opportunities:
            try:
                result = qualifier.assess_opportunity(opp)
                
                if not result.get('error'):
                    if result.get('relevance_score', 0) == 0:
                        logger.info(f"✓ Handled malformed opportunity correctly: {opp.get('noticeId')}")
                    else:
                        self.add_result(
                            "MEDIUM",
                            "OPENAI_MALFORMED_DATA_SCORE",
                            f"Gave non-zero score to malformed data: {opp}",
                            "May generate false positives on bad data",
                            "Add input validation before AI assessment"
                        )
            except Exception as e:
                self.add_result(
                    "HIGH",
                    "OPENAI_MALFORMED_DATA_ERROR",
                    f"System crashed on malformed data {opp}: {str(e)}",
                    "Application fails on malformed RFP data",
                    "Add comprehensive input validation"
                )

    def _test_openai_model_availability(self):
        """Test OpenAI model availability and fallback"""
        if not Config.OPENAI_API_KEY:
            return
            
        # Test with non-existent model
        with patch('ai_qualifier.AIQualifier.__init__') as mock_init:
            mock_init.return_value = None
            
            # Create qualifier with fake model
            qualifier = AIQualifier.__new__(AIQualifier)
            qualifier.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            qualifier.model = "gpt-nonexistent-model"
            qualifier.circuit_breaker = None
            qualifier.past_rfps = ""
            
            test_opportunity = {
                "title": "Test Opportunity",
                "description": "Test description",
                "noticeId": "test_model_availability"
            }
            
            try:
                result = qualifier._single_phase_assessment(test_opportunity, Config.get_company_name())
                
                if result.get('error'):
                    logger.info("✓ Correctly handled non-existent model")
                elif result.get('fallback_model'):
                    logger.info("✓ Successfully used fallback model")
                else:
                    self.add_result(
                        "MEDIUM",
                        "OPENAI_MODEL_AVAILABILITY",
                        "System didn't handle model unavailability clearly",
                        "May fail silently when models are unavailable",
                        "Implement model availability checks and fallbacks"
                    )
            except Exception as e:
                if "model" in str(e).lower():
                    logger.info("✓ Correctly failed on invalid model")
                else:
                    self.add_result(
                        "HIGH",
                        "OPENAI_MODEL_ERROR",
                        f"Unexpected model error: {str(e)}",
                        "Poor model error handling",
                        "Improve model availability error handling"
                    )

    def test_google_sheets_failures(self):
        """Test Google Sheets API failure scenarios"""
        logger.info("Testing Google Sheets API failure modes...")
        
        # Test with invalid credentials
        self._test_sheets_invalid_credentials()
        
        # Test permission issues
        self._test_sheets_permissions()
        
        # Test quota limits
        self._test_sheets_quota_limits()
        
        # Test concurrent writes
        self._test_sheets_concurrent_writes()
        
        # Test malformed data
        self._test_sheets_malformed_data()

    def _test_sheets_invalid_credentials(self):
        """Test Sheets API with invalid credentials"""
        try:
            # Try to create SheetsManager with non-existent credentials file
            fake_manager = SheetsManager("/fake/path/to/credentials.json")
            self.add_result(
                "HIGH",
                "SHEETS_INVALID_CREDS_NO_ERROR",
                "SheetsManager created with invalid credentials path",
                "System may fail at runtime instead of startup",
                "Validate credentials file at initialization"
            )
        except Exception as e:
            logger.info("✓ Correctly failed on invalid credentials file")
            
        # Test with malformed credentials content
        try:
            with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
                mock_creds.side_effect = ValueError("Invalid credentials format")
                
                fake_manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                self.add_result(
                    "HIGH",
                    "SHEETS_MALFORMED_CREDS",
                    "SheetsManager created with malformed credentials",
                    "System may fail unpredictably",
                    "Add credentials validation"
                )
        except Exception as e:
            logger.info("✓ Correctly failed on malformed credentials")

    def _test_sheets_permissions(self):
        """Test Sheets API permission issues"""
        if not Config.GOOGLE_SHEETS_CREDS_PATH:
            self.add_result("CRITICAL", "SHEETS_NO_CREDENTIALS", 
                          "Google Sheets credentials not configured",
                          "Cannot track RFPs or generate reports", 
                          "Configure GOOGLE_SHEETS_CREDS_PATH")
            return
            
        try:
            manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
            
            # Try to access a sheet we don't have permission for
            fake_sheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"  # Public sample sheet
            
            try:
                existing_ids = manager.get_existing_notice_ids(fake_sheet_id)
                if existing_ids:
                    logger.info("✓ Successfully accessed public sheet")
                else:
                    logger.info("✓ Gracefully handled permission issue")
            except Exception as e:
                if "403" in str(e) or "permission" in str(e).lower():
                    logger.info("✓ Correctly handled permission error")
                else:
                    self.add_result(
                        "MEDIUM",
                        "SHEETS_PERMISSION_ERROR_HANDLING",
                        f"Unexpected permission error: {str(e)}",
                        "Poor permission error handling",
                        "Improve permission error messages"
                    )
                    
        except Exception as e:
            logger.error(f"Sheets permission test failed: {str(e)}")

    def _test_sheets_quota_limits(self):
        """Test Google Sheets quota limit handling"""
        if not Config.GOOGLE_SHEETS_CREDS_PATH:
            return
            
        # This is difficult to test without actually hitting quotas
        # Instead, we'll simulate quota errors
        try:
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = MagicMock()
                mock_service.spreadsheets().values().get().execute.side_effect = Exception("Quota exceeded")
                mock_build.return_value = mock_service
                
                manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                
                result = manager.get_existing_notice_ids("test_sheet_id")
                
                if result == set():
                    logger.info("✓ Handled quota error gracefully")
                else:
                    self.add_result(
                        "MEDIUM",
                        "SHEETS_QUOTA_HANDLING",
                        "System didn't handle quota error properly",
                        "May continue processing with stale data",
                        "Implement quota error detection and backoff"
                    )
        except Exception as e:
            logger.error(f"Quota limit test failed: {str(e)}")

    def _test_sheets_concurrent_writes(self):
        """Test concurrent write operations to sheets"""
        if not Config.GOOGLE_SHEETS_CREDS_PATH or not Config.SPAM_SPREADSHEET_ID:
            return
            
        def write_opportunity(thread_id):
            try:
                manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                
                fake_opportunity = {
                    "title": f"Test Opportunity {thread_id}",
                    "noticeId": f"test_{thread_id}_{int(time.time())}",
                    "fullParentPathName": "Test Agency",
                    "postedDate": "2024-01-01"
                }
                
                fake_assessment = {
                    "relevance_score": random.randint(1, 10),
                    "is_qualified": False,
                    "justification": f"Test assessment {thread_id}"
                }
                
                manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, fake_opportunity, fake_assessment)
                return True
            except Exception as e:
                logger.error(f"Thread {thread_id} failed: {str(e)}")
                return False
        
        # Launch concurrent writes
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(write_opportunity, i) for i in range(5)]
                
                successes = sum(1 for future in concurrent.futures.as_completed(futures) if future.result())
                
                if successes >= 3:  # At least 3 out of 5 should succeed
                    logger.info(f"✓ Concurrent writes mostly successful ({successes}/5)")
                else:
                    self.add_result(
                        "MEDIUM",
                        "SHEETS_CONCURRENT_WRITE_FAILURES",
                        f"Only {successes}/5 concurrent writes succeeded",
                        "System may lose data under concurrent load",
                        "Implement write queuing or locking mechanism"
                    )
        except Exception as e:
            self.add_result(
                "HIGH",
                "SHEETS_CONCURRENT_WRITE_ERROR",
                f"Concurrent write test failed: {str(e)}",
                "System may not handle concurrent operations",
                "Test and improve concurrent access handling"
            )

    def _test_sheets_malformed_data(self):
        """Test sheets handling of malformed data"""
        if not Config.GOOGLE_SHEETS_CREDS_PATH:
            return
            
        try:
            manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
            
            # Test with malformed opportunity data
            malformed_opportunities = [
                {"title": None, "noticeId": None},  # Null values
                {},  # Empty dict
                {"title": "x" * 1000, "noticeId": "test_long"},  # Very long strings
                {"title": "Test\n\r\tSpecial", "noticeId": "test_special"},  # Special characters
            ]
            
            for i, opp in enumerate(malformed_opportunities):
                try:
                    fake_assessment = {"relevance_score": 1, "is_qualified": False, "justification": "Test"}
                    
                    # This should either work or fail gracefully
                    if Config.SPAM_SPREADSHEET_ID:
                        manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, opp, fake_assessment)
                        logger.info(f"✓ Handled malformed data {i}")
                    
                except Exception as e:
                    if "invalid" in str(e).lower() or "malformed" in str(e).lower():
                        logger.info(f"✓ Correctly rejected malformed data {i}")
                    else:
                        self.add_result(
                            "MEDIUM",
                            "SHEETS_MALFORMED_DATA_ERROR",
                            f"Unexpected error with malformed data: {str(e)}",
                            "System may crash on malformed RFP data",
                            "Add input validation before sheet operations"
                        )
        except Exception as e:
            logger.error(f"Malformed data test failed: {str(e)}")

    def test_google_drive_failures(self):
        """Test Google Drive API failure scenarios"""
        logger.info("Testing Google Drive API failure modes...")
        
        # Test with invalid credentials
        self._test_drive_invalid_credentials()
        
        # Test upload failures
        self._test_drive_upload_failures()
        
        # Test folder creation issues
        self._test_drive_folder_creation_failures()
        
        # Test large file handling
        self._test_drive_large_files()

    def _test_drive_invalid_credentials(self):
        """Test Drive API with invalid credentials"""
        try:
            fake_manager = DriveManager("/fake/path/to/credentials.json")
            self.add_result(
                "HIGH",
                "DRIVE_INVALID_CREDS_NO_ERROR",
                "DriveManager created with invalid credentials",
                "System may fail at runtime instead of startup",
                "Validate Drive credentials at initialization"
            )
        except Exception as e:
            logger.info("✓ Correctly failed on invalid Drive credentials")

    def _test_drive_upload_failures(self):
        """Test Drive upload failure scenarios"""
        if not Config.GOOGLE_SHEETS_CREDS_PATH:
            return
            
        try:
            # Mock network failures during upload
            with patch('googleapiclient.http.MediaIoBaseUpload') as mock_media:
                mock_media.side_effect = Exception("Network error during upload")
                
                manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                
                result = manager.upload_file(b"test data", "test.txt", "fake_folder_id")
                
                if result is None:
                    logger.info("✓ Gracefully handled upload failure")
                else:
                    self.add_result(
                        "HIGH",
                        "DRIVE_UPLOAD_FAILURE_NOT_HANDLED",
                        "System reported success despite upload failure",
                        "May lose important RFP attachments",
                        "Improve upload error detection and retry logic"
                    )
        except Exception as e:
            logger.error(f"Drive upload test failed: {str(e)}")

    def _test_drive_folder_creation_failures(self):
        """Test Drive folder creation failures"""
        if not Config.GOOGLE_SHEETS_CREDS_PATH:
            return
            
        try:
            # Mock folder creation failure
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = MagicMock()
                mock_service.files().create().execute.side_effect = Exception("Folder creation failed")
                mock_build.return_value = mock_service
                
                manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                
                try:
                    folder_id = manager.create_folder("Test Folder")
                    
                    self.add_result(
                        "HIGH",
                        "DRIVE_FOLDER_FAILURE_NOT_HANDLED",
                        "System reported folder creation success despite failure",
                        "May lose RFP organization structure",
                        "Improve folder creation error handling"
                    )
                except Exception as e:
                    logger.info("✓ Correctly failed on folder creation error")
                    
        except Exception as e:
            logger.error(f"Drive folder test failed: {str(e)}")

    def _test_drive_large_files(self):
        """Test Drive handling of large files"""
        if not Config.GOOGLE_SHEETS_CREDS_PATH:
            return
            
        try:
            manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
            
            # Create a large fake file (10MB)
            large_data = b"x" * (10 * 1024 * 1024)
            
            start_time = time.time()
            
            # This will fail without a real folder, but we can test the timing
            try:
                result = manager.upload_file(large_data, "large_test.dat", "fake_folder")
            except:
                pass  # Expected to fail
                
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 60:  # More than 1 minute
                self.add_result(
                    "LOW",
                    "DRIVE_SLOW_LARGE_FILES",
                    f"Large file processing took {duration:.1f} seconds",
                    "May timeout on large RFP attachments",
                    "Implement progress indicators and timeout handling for large files"
                )
            
        except Exception as e:
            logger.error(f"Large file test failed: {str(e)}")

    def test_network_failures(self):
        """Test network-related failure scenarios"""
        logger.info("Testing network failure scenarios...")
        
        # Test complete network failure simulation
        self._test_complete_network_failure()
        
        # Test intermittent connectivity
        self._test_intermittent_connectivity()
        
        # Test DNS resolution failures
        self._test_dns_failures()

    def _test_complete_network_failure(self):
        """Test system behavior with complete network failure"""
        # Mock all network requests to fail
        with patch('requests.Session.get') as mock_get, \
             patch('openai.OpenAI.chat.completions.create') as mock_openai, \
             patch('googleapiclient.discovery.build') as mock_google:
            
            mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
            mock_openai.side_effect = openai.APIConnectionError("Network unreachable")
            mock_google.side_effect = Exception("Network unreachable")
            
            # Test if system handles complete network failure gracefully
            errors_caught = 0
            
            # Test SAM API
            try:
                if Config.SAM_API_KEY:
                    client = SAMClient(Config.SAM_API_KEY)
                    client.search_by_naics("541511", "01/01/2024", "01/02/2024")
            except Exception as e:
                if "network" in str(e).lower() or "connection" in str(e).lower():
                    errors_caught += 1
            
            # Test OpenAI API
            try:
                if Config.OPENAI_API_KEY:
                    qualifier = AIQualifier(Config.OPENAI_API_KEY)
                    qualifier.assess_opportunity({"title": "test", "noticeId": "test"})
            except Exception as e:
                if "network" in str(e).lower() or "connection" in str(e).lower():
                    errors_caught += 1
            
            if errors_caught >= 1:
                logger.info("✓ System correctly detects network failures")
            else:
                self.add_result(
                    "HIGH",
                    "NETWORK_FAILURE_NOT_DETECTED",
                    "System didn't properly detect network failures",
                    "May appear to work while actually failing",
                    "Add network connectivity checks and clear error messages"
                )

    def _test_intermittent_connectivity(self):
        """Test intermittent network connectivity"""
        # This is complex to simulate, so we'll do a simplified version
        request_count = 0
        
        def mock_intermittent_request(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            if request_count % 3 == 0:  # Fail every 3rd request
                raise requests.exceptions.ConnectionError("Intermittent failure")
            return MagicMock(status_code=200, json=lambda: {"opportunitiesData": [], "totalRecords": 0})
        
        with patch('requests.Session.get', side_effect=mock_intermittent_request):
            if Config.SAM_API_KEY:
                client = SAMClient(Config.SAM_API_KEY)
                
                successes = 0
                failures = 0
                
                for i in range(6):  # Make 6 requests
                    try:
                        client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                        successes += 1
                    except:
                        failures += 1
                
                if failures > 0 and successes > 0:
                    logger.info(f"✓ Handled intermittent connectivity: {successes} successes, {failures} failures")
                elif failures == 0:
                    self.add_result(
                        "MEDIUM",
                        "INTERMITTENT_NETWORK_NOT_DETECTED",
                        "System didn't detect intermittent network issues",
                        "May not retry on temporary failures",
                        "Implement retry logic for transient network errors"
                    )

    def _test_dns_failures(self):
        """Test DNS resolution failures"""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Name resolution failed")
            
            if Config.SAM_API_KEY:
                try:
                    client = SAMClient(Config.SAM_API_KEY)
                    client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                    
                    self.add_result(
                        "MEDIUM",
                        "DNS_FAILURE_NOT_DETECTED",
                        "System didn't detect DNS resolution failure",
                        "May appear to hang on DNS issues",
                        "Add DNS resolution timeout and error handling"
                    )
                except Exception as e:
                    if "resolution" in str(e).lower() or "name" in str(e).lower():
                        logger.info("✓ Correctly detected DNS failure")
                    else:
                        logger.info("✓ Correctly detected network error (DNS-related)")

    def test_credential_failures(self):
        """Test various credential failure scenarios"""
        logger.info("Testing credential failure scenarios...")
        
        # Test missing environment variables
        self._test_missing_env_vars()
        
        # Test expired credentials
        self._test_expired_credentials()

    def _test_missing_env_vars(self):
        """Test behavior when environment variables are missing"""
        critical_vars = ['SAM_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_SHEETS_CREDS_PATH']
        
        for var in critical_vars:
            if not getattr(Config, var):
                self.add_result(
                    "CRITICAL",
                    f"MISSING_{var}",
                    f"{var} environment variable not set",
                    "Core functionality unavailable",
                    f"Configure {var} environment variable"
                )

    def _test_expired_credentials(self):
        """Test handling of expired credentials"""
        # This is difficult to test without actually expired credentials
        # We'll simulate the error responses
        
        with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
            mock_creds.side_effect = Exception("Token has expired")
            
            try:
                manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH or "/fake/path")
                self.add_result(
                    "HIGH",
                    "EXPIRED_GOOGLE_CREDS_NOT_DETECTED",
                    "System didn't detect expired Google credentials",
                    "May fail at runtime with unclear errors",
                    "Add credential expiration detection"
                )
            except Exception as e:
                if "expired" in str(e).lower() or "token" in str(e).lower():
                    logger.info("✓ Correctly detected expired Google credentials")

    def test_concurrent_operations(self):
        """Test system behavior under concurrent load"""
        logger.info("Testing concurrent operations...")
        
        def concurrent_sam_requests():
            if not Config.SAM_API_KEY:
                return False
            try:
                client = SAMClient(Config.SAM_API_KEY)
                client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                return True
            except:
                return False
        
        def concurrent_ai_assessments():
            if not Config.OPENAI_API_KEY:
                return False
            try:
                qualifier = AIQualifier(Config.OPENAI_API_KEY)
                qualifier.assess_opportunity({"title": "test", "noticeId": f"concurrent_{time.time()}"})
                return True
            except:
                return False
        
        # Test concurrent operations
        operations = [concurrent_sam_requests, concurrent_ai_assessments]
        
        for op in operations:
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(op) for _ in range(3)]
                    
                    successes = sum(1 for future in concurrent.futures.as_completed(futures) if future.result())
                    
                    if successes >= 2:  # At least 2 out of 3 should succeed
                        logger.info(f"✓ Concurrent {op.__name__} mostly successful ({successes}/3)")
                    else:
                        self.add_result(
                            "MEDIUM",
                            f"CONCURRENT_{op.__name__.upper()}_FAILURES",
                            f"Only {successes}/3 concurrent {op.__name__} succeeded",
                            "System may not handle concurrent load well",
                            "Test and improve concurrent operation handling"
                        )
            except Exception as e:
                logger.error(f"Concurrent test {op.__name__} failed: {str(e)}")

    def test_data_corruption_scenarios(self):
        """Test data corruption and validation scenarios"""
        logger.info("Testing data corruption scenarios...")
        
        # Test malformed JSON in various contexts
        self._test_malformed_json_handling()
        
        # Test encoding issues
        self._test_encoding_issues()

    def _test_malformed_json_handling(self):
        """Test handling of malformed JSON data"""
        malformed_json_strings = [
            '{"incomplete": true',  # Missing closing brace
            '{"duplicate_keys": 1, "duplicate_keys": 2}',  # Duplicate keys
            '{"unicode": "\\uXXXX"}',  # Invalid unicode
            '',  # Empty string
            'null',  # Just null
            '[]',  # Array instead of object
        ]
        
        for i, json_str in enumerate(malformed_json_strings):
            try:
                result = json.loads(json_str)
                logger.info(f"✓ Python handled malformed JSON {i}: {json_str[:30]}")
            except json.JSONDecodeError:
                logger.info(f"✓ Python correctly rejected malformed JSON {i}")
            except Exception as e:
                logger.warning(f"Unexpected JSON error {i}: {str(e)}")

    def _test_encoding_issues(self):
        """Test handling of encoding issues"""
        problematic_strings = [
            "Test with emoji: 🚀💻🔍",  # Emoji
            "Test with unicode: àáâãäåæçèé",  # Extended Latin
            "Test with Chinese: 测试数据",  # Chinese characters
            "Test with RTL: العربية",  # Arabic (RTL)
            b"Test bytes".decode('utf-8', errors='ignore'),  # Bytes to string
        ]
        
        for i, test_string in enumerate(problematic_strings):
            try:
                # Test if string can be safely encoded/decoded
                encoded = test_string.encode('utf-8')
                decoded = encoded.decode('utf-8')
                
                if decoded == test_string:
                    logger.info(f"✓ Handled encoding test {i}: {test_string[:20]}...")
                else:
                    self.add_result(
                        "LOW",
                        f"ENCODING_ISSUE_{i}",
                        f"Encoding/decoding changed string: {test_string[:30]}",
                        "May cause data corruption in RFP text",
                        "Use consistent UTF-8 encoding throughout"
                    )
            except Exception as e:
                self.add_result(
                    "MEDIUM",
                    f"ENCODING_ERROR_{i}",
                    f"Encoding error with string {test_string[:30]}: {str(e)}",
                    "System may crash on international RFP content",
                    "Add robust encoding error handling"
                )

    def generate_vulnerability_report(self):
        """Generate comprehensive vulnerability report"""
        logger.info("Generating vulnerability report...")
        
        report = {
            'test_summary': {
                'total_tests': len(self.test_results),
                'critical_issues': len(self.vulnerability_report['critical_vulnerabilities']),
                'high_risk_issues': len(self.vulnerability_report['high_risk_issues']),
                'medium_risk_issues': len(self.vulnerability_report['medium_risk_issues']),
                'low_risk_issues': len(self.vulnerability_report['low_risk_issues']),
                'timestamp': datetime.now().isoformat()
            },
            'executive_summary': self._generate_executive_summary(),
            'detailed_findings': self.vulnerability_report,
            'recommendations': self._generate_recommendations(),
            'test_results': self.test_results
        }
        
        # Save report to file
        report_filename = f"api_vulnerability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Vulnerability report saved to {report_filename}")
        
        # Print summary
        self._print_report_summary(report)
        
        return report

    def _generate_executive_summary(self):
        """Generate executive summary of findings"""
        critical_count = len(self.vulnerability_report['critical_vulnerabilities'])
        high_count = len(self.vulnerability_report['high_risk_issues'])
        medium_count = len(self.vulnerability_report['medium_risk_issues'])
        low_count = len(self.vulnerability_report['low_risk_issues'])
        
        summary = f"""
API FAILURE TESTING EXECUTIVE SUMMARY

Total Issues Found: {critical_count + high_count + medium_count + low_count}
- Critical: {critical_count} (require immediate attention)
- High Risk: {high_count} (should be addressed soon)
- Medium Risk: {medium_count} (should be planned for resolution)
- Low Risk: {low_count} (minor improvements)

CRITICAL ISSUES:
"""
        
        for vuln in self.vulnerability_report['critical_vulnerabilities']:
            summary += f"- {vuln['test_name']}: {vuln['description']}\n"
        
        if critical_count == 0:
            summary += "- No critical vulnerabilities found\n"
        
        summary += f"""
HIGH RISK ISSUES:
"""
        
        for vuln in self.vulnerability_report['high_risk_issues'][:3]:  # Show top 3
            summary += f"- {vuln['test_name']}: {vuln['description']}\n"
        
        if high_count > 3:
            summary += f"- ... and {high_count - 3} more high-risk issues\n"
        elif high_count == 0:
            summary += "- No high-risk vulnerabilities found\n"
        
        return summary.strip()

    def _generate_recommendations(self):
        """Generate prioritized recommendations"""
        recommendations = []
        
        # Critical recommendations
        for vuln in self.vulnerability_report['critical_vulnerabilities']:
            if vuln.get('recommendation'):
                recommendations.append({
                    'priority': 'CRITICAL',
                    'recommendation': vuln['recommendation'],
                    'context': vuln['test_name']
                })
        
        # High priority recommendations  
        for vuln in self.vulnerability_report['high_risk_issues']:
            if vuln.get('recommendation'):
                recommendations.append({
                    'priority': 'HIGH',
                    'recommendation': vuln['recommendation'],
                    'context': vuln['test_name']
                })
        
        # General recommendations
        general_recommendations = [
            {
                'priority': 'HIGH',
                'recommendation': 'Implement comprehensive error logging and monitoring',
                'context': 'System-wide'
            },
            {
                'priority': 'MEDIUM',
                'recommendation': 'Add health check endpoints for all APIs',
                'context': 'System-wide'
            },
            {
                'priority': 'MEDIUM',
                'recommendation': 'Implement circuit breakers for external API calls',
                'context': 'System-wide'
            },
            {
                'priority': 'LOW',
                'recommendation': 'Add performance monitoring and alerting',
                'context': 'System-wide'
            }
        ]
        
        recommendations.extend(general_recommendations)
        
        return recommendations

    def _print_report_summary(self, report):
        """Print a summary of the vulnerability report to console"""
        print("\n" + "="*80)
        print("API VULNERABILITY TEST RESULTS")
        print("="*80)
        
        summary = report['test_summary']
        print(f"Total Tests Run: {summary['total_tests']}")
        print(f"Critical Issues: {summary['critical_issues']}")
        print(f"High Risk Issues: {summary['high_risk_issues']}")
        print(f"Medium Risk Issues: {summary['medium_risk_issues']}")
        print(f"Low Risk Issues: {summary['low_risk_issues']}")
        
        if summary['critical_issues'] > 0:
            print("\n🚨 CRITICAL ISSUES FOUND:")
            for vuln in report['detailed_findings']['critical_vulnerabilities']:
                print(f"  - {vuln['test_name']}: {vuln['description']}")
        
        if summary['high_risk_issues'] > 0:
            print("\n⚠️  HIGH RISK ISSUES:")
            for vuln in report['detailed_findings']['high_risk_issues'][:5]:
                print(f"  - {vuln['test_name']}: {vuln['description']}")
        
        print(f"\nFull report saved to: api_vulnerability_report_*.json")
        print("="*80)

def main():
    """Main function to run API failure tests"""
    print("Starting comprehensive API failure testing...")
    
    tester = APIFailureTester()
    report = tester.run_all_tests()
    
    # Return summary for any automated processes
    return {
        'critical_count': len(report['critical_vulnerabilities']),
        'high_count': len(report['high_risk_issues']),
        'medium_count': len(report['medium_risk_issues']),
        'low_count': len(report['low_risk_issues']),
        'total_issues': len(report['critical_vulnerabilities']) + len(report['high_risk_issues']) + len(report['medium_risk_issues']) + len(report['low_risk_issues'])
    }

if __name__ == "__main__":
    main()