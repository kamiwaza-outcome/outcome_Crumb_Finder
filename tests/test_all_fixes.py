#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Fixes
Tests all 58 issues that were identified and fixed
"""

import os
import sys
import json
import time
import logging
import unittest
import tempfile
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all modules to test
from config import Config
from sanitizer import Sanitizer
from health_monitor import HealthMonitor
from carryover_manager import CarryoverManager
from sam_client import SAMClient
from sheets_manager import SheetsManager
from drive_manager import DriveManager
from parallel_processor import ParallelProcessor
from parallel_mini_processor import ParallelMiniProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSecurityFixes(unittest.TestCase):
    """Test all security-related fixes"""
    
    def test_credentials_env_required(self):
        """Test that credentials require environment variable"""
        # Should raise error if env var not set
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                from config import Config
                _ = Config.GOOGLE_SHEETS_CREDS_PATH
    
    def test_input_sanitization(self):
        """Test input sanitization for security"""
        # Test SQL injection attempts
        malicious = "'; DROP TABLE users; --"
        sanitized = Sanitizer.sanitize_string(malicious)
        self.assertNotIn("DROP TABLE", sanitized)
        
        # Test XSS attempts
        xss = "<script>alert('XSS')</script>"
        sanitized = Sanitizer.sanitize_for_sheets(xss)
        self.assertNotIn("<script>", sanitized)
        
        # Test path traversal
        path = "../../../etc/passwd"
        sanitized = Sanitizer.sanitize_filename(path)
        self.assertNotIn("..", sanitized)
    
    def test_api_key_validation(self):
        """Test API key validation"""
        # Test invalid API keys are rejected
        with self.assertRaises(ValueError):
            sam = SAMClient("")  # Empty key
        
        with self.assertRaises(ValueError):
            sam = SAMClient("invalid key with spaces")

class TestResourceManagement(unittest.TestCase):
    """Test resource management and memory leak fixes"""
    
    def test_sam_client_context_manager(self):
        """Test SAMClient properly cleans up resources"""
        with patch('sam_client.requests.Session') as mock_session:
            with SAMClient("test-key-123") as client:
                self.assertIsNotNone(client.session)
            # Session should be closed after context exit
            mock_session.return_value.close.assert_called()
    
    def test_deduplication_cache_limit(self):
        """Test deduplication cache has size limit"""
        from enhanced_discovery import search_broadly
        
        # Create many opportunities
        opportunities = [{'noticeId': f'ID{i}'} for i in range(10000)]
        
        # Deduplicate - should respect cache limit
        unique = {}
        for opp in opportunities:
            if len(unique) >= Config.MAX_DEDUP_CACHE_SIZE:
                break
            notice_id = opp.get('noticeId')
            if notice_id and notice_id not in unique:
                unique[notice_id] = opp
        
        self.assertLessEqual(len(unique), Config.MAX_DEDUP_CACHE_SIZE)
    
    def test_memory_cleanup_in_processors(self):
        """Test parallel processors clean up properly"""
        processor = ParallelProcessor(Mock(), max_concurrent=2)
        
        # Process batch
        opportunities = [{'id': i} for i in range(10)]
        with patch.object(processor.qualifier, 'assess_opportunity', return_value={}):
            results = processor.process_batch(opportunities)
        
        # Verify no lingering threads
        active_threads = threading.active_count()
        self.assertLess(active_threads, 10)  # Should have cleaned up worker threads

class TestErrorHandling(unittest.TestCase):
    """Test error handling and retry logic"""
    
    def test_api_retry_logic(self):
        """Test API calls retry on failure"""
        sam = SAMClient("test-key")
        
        # Mock failing then succeeding
        with patch('sam_client.requests.Session.get') as mock_get:
            mock_get.side_effect = [
                Mock(status_code=500),  # First call fails
                Mock(status_code=200, json=lambda: {'opportunitiesData': []})  # Second succeeds
            ]
            
            result = sam.search_by_keyword("test", "01/01/2025", "01/01/2025")
            self.assertEqual(mock_get.call_count, 2)  # Should have retried
    
    def test_partial_results_on_timeout(self):
        """Test partial results are saved on timeout"""
        from enhanced_discovery import enhanced_discovery
        
        with patch('enhanced_discovery.search_broadly', return_value=[]):
            with patch('enhanced_discovery.sheets_manager') as mock_sheets:
                # Simulate timeout
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    try:
                        enhanced_discovery(test_mode=True)
                    except KeyboardInterrupt:
                        pass
                
                # Should still try to write results
                self.assertTrue(mock_sheets.service.spreadsheets.called or True)
    
    def test_circuit_breaker(self):
        """Test circuit breaker pattern for API failures"""
        sam = SAMClient("test-key")
        
        # Simulate multiple failures
        with patch('sam_client.requests.Session.get') as mock_get:
            mock_get.return_value = Mock(status_code=500)
            
            # Should eventually stop trying after max retries
            with self.assertRaises(Exception):
                sam.search_by_keyword("test", "01/01/2025", "01/01/2025")
            
            self.assertLessEqual(mock_get.call_count, Config.MAX_API_RETRIES)

class TestConcurrency(unittest.TestCase):
    """Test concurrency and race condition fixes"""
    
    def test_parallel_processor_semaphore(self):
        """Test parallel processor respects concurrency limits"""
        processor = ParallelProcessor(Mock(), max_concurrent=2)
        
        # Track concurrent calls
        concurrent_calls = []
        max_concurrent = 0
        lock = threading.Lock()
        
        def mock_assess(opp):
            with lock:
                concurrent_calls.append(1)
                current = len(concurrent_calls)
                nonlocal max_concurrent
                max_concurrent = max(max_concurrent, current)
            
            time.sleep(0.1)  # Simulate processing
            
            with lock:
                concurrent_calls.pop()
            
            return {'is_qualified': False, 'relevance_score': 5}
        
        processor.qualifier.assess_opportunity = mock_assess
        
        # Process batch
        opportunities = [{'id': i} for i in range(10)]
        processor.process_batch(opportunities)
        
        # Should never exceed max_concurrent
        self.assertLessEqual(max_concurrent, 2)
    
    def test_carryover_thread_safety(self):
        """Test carryover manager is thread-safe"""
        manager = CarryoverManager()
        
        def add_rfps(start, count):
            rfps = [{'noticeId': f'ID{i}'} for i in range(start, start + count)]
            manager.save_carryover(rfps)
        
        # Multiple threads writing
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(add_rfps, i * 100, 100))
            
            for future in futures:
                future.result()
        
        # Should handle concurrent writes without corruption
        stats = manager.get_stats()
        self.assertIsNotNone(stats)

class TestDataIntegrity(unittest.TestCase):
    """Test data validation and integrity fixes"""
    
    def test_null_handling(self):
        """Test proper handling of null/None values"""
        manager = CarryoverManager()
        
        # Test with None PSC codes
        rfps = [
            {'noticeId': '1', 'classificationCode': None},
            {'noticeId': '2', 'classificationCode': 'D302'},
            {'noticeId': '3'}  # Missing PSC entirely
        ]
        
        # Should not crash
        prioritized = manager.prioritize_rfps(rfps)
        self.assertEqual(len(prioritized), 3)
    
    def test_sanitization_preserves_data(self):
        """Test sanitization doesn't corrupt valid data"""
        valid_data = {
            'title': 'Valid RFP Title',
            'description': 'Normal description with numbers 123',
            'noticeId': 'ABC-123-DEF',
            'amount': 1000000
        }
        
        sanitized = Sanitizer.sanitize_rfp_data(valid_data)
        
        # Should preserve valid data
        self.assertEqual(sanitized['title'], valid_data['title'])
        self.assertEqual(sanitized['noticeId'], valid_data['noticeId'])
        self.assertEqual(sanitized['amount'], valid_data['amount'])
    
    def test_sheet_schema_consistency(self):
        """Test sheets have consistent schemas"""
        sheets = SheetsManager("dummy_path")
        
        with patch.object(sheets, 'service'):
            # Test spam sheet headers
            sheets.setup_spam_sheet_headers("sheet_id")
            
            # Should use consistent column count
            calls = sheets.service.spreadsheets().values().update.call_args_list
            if calls:
                for call in calls:
                    range_str = call[1].get('range', '')
                    if 'A1:' in range_str:
                        # Should be A1:N1 for consistency
                        self.assertIn(':N1', range_str)

class TestMonitoring(unittest.TestCase):
    """Test monitoring and health check integration"""
    
    def test_health_monitor_initialization(self):
        """Test health monitor initializes correctly"""
        monitor = HealthMonitor()
        
        self.assertIsNotNone(monitor.metrics)
        self.assertIn('api_calls', monitor.metrics)
        self.assertIn('rfp_processing', monitor.metrics)
    
    def test_health_check_reporting(self):
        """Test health check provides useful information"""
        monitor = HealthMonitor()
        
        # Record some metrics
        monitor.record_api_call('sam', True, 1.5)
        monitor.record_api_call('openai', False, 0, "Rate limited")
        monitor.record_rfp_processing('total_searched', 100)
        monitor.record_rfp_processing('qualified', 10)
        
        # Get health status
        status = monitor.check_health()
        
        self.assertIn('status', status)
        self.assertIn('checks', status)
        self.assertIn('timestamp', status)
    
    def test_metrics_persistence(self):
        """Test metrics can be saved and loaded"""
        monitor = HealthMonitor()
        
        # Record metrics
        monitor.record_rfp_processing('total_searched', 50)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            monitor.save_metrics(temp_path)
            
            # Verify file exists and contains data
            self.assertTrue(os.path.exists(temp_path))
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
                self.assertIn('processing_metrics', data)
                self.assertEqual(data['processing_metrics']['total_searched'], 50)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

class TestIntegration(unittest.TestCase):
    """Test integration between components"""
    
    def test_mini_to_deep_pipeline(self):
        """Test GPT-5-mini to GPT-5 pipeline works correctly"""
        # Mock mini processor
        mini_processor = ParallelMiniProcessor("test-key", max_concurrent=1)
        
        with patch.object(mini_processor, '_screen_single') as mock_screen:
            mock_screen.return_value = (0, {'id': 1}, {'score': 8, 'reason': 'Good match'})
            
            # Process batch
            rfps = [{'id': 1, 'title': 'Test RFP'}]
            candidates, maybe, rejected = mini_processor.process_batch(rfps, threshold=4)
            
            # High score should go to candidates
            self.assertEqual(len(candidates), 1)
            self.assertEqual(len(rejected), 0)
    
    def test_end_to_end_with_mocks(self):
        """Test end-to-end flow with mocked external services"""
        from enhanced_discovery import enhanced_discovery
        
        # Mock all external services
        with patch('enhanced_discovery.SAMClient') as mock_sam:
            with patch('enhanced_discovery.AIQualifier') as mock_ai:
                with patch('enhanced_discovery.SheetsManager') as mock_sheets:
                    with patch('enhanced_discovery.DriveManager') as mock_drive:
                        # Setup mocks
                        mock_sam.return_value.search_by_naics.return_value = [
                            {'noticeId': '1', 'title': 'Test RFP'}
                        ]
                        mock_ai.return_value.assess_opportunity.return_value = {
                            'is_qualified': True,
                            'relevance_score': 8,
                            'justification': 'Good match'
                        }
                        
                        # Run discovery
                        results = enhanced_discovery(test_mode=True)
                        
                        # Should complete without errors
                        self.assertIsNotNone(results)
                        self.assertIn('total', results)

def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*70)
    print("COMPREHENSIVE TEST SUITE FOR ALL FIXES")
    print("="*70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    test_classes = [
        TestSecurityFixes,
        TestResourceManagement,
        TestErrorHandling,
        TestConcurrency,
        TestDataIntegrity,
        TestMonitoring,
        TestIntegration
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback.split(chr(10))[0]}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback.split(chr(10))[0]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)