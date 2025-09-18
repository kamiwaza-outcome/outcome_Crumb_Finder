#!/usr/bin/env python3
"""Debug script to find where hanging occurs"""

import sys
import time

print("Step 1: Starting imports...")
sys.stdout.flush()

print("Step 2: Importing dotenv...")
sys.stdout.flush()
from dotenv import load_dotenv

print("Step 3: Loading .env...")
sys.stdout.flush()
load_dotenv()

print("Step 4: Importing config...")
sys.stdout.flush()
from config import Config

print("Step 5: Importing parallel modules...")
sys.stdout.flush()
from parallel_mini_processor import ParallelMiniProcessor
from parallel_processor import ParallelProcessor

print("Step 6: Importing ai_qualifier...")
sys.stdout.flush()
from ai_qualifier import AIQualifier

print("Step 7: Creating instances...")
sys.stdout.flush()

print("Step 7a: Creating ParallelMiniProcessor...")
sys.stdout.flush()
mini_processor = ParallelMiniProcessor(
    Config.OPENAI_API_KEY, 
    max_concurrent=Config.MAX_CONCURRENT_MINI
)

print("Step 7b: Creating AIQualifier...")
sys.stdout.flush()
qualifier = AIQualifier(Config.OPENAI_API_KEY)

print("Step 7c: Creating ParallelProcessor...")
sys.stdout.flush()
deep_processor = ParallelProcessor(
    qualifier,
    max_concurrent=Config.MAX_CONCURRENT_DEEP
)

print("Step 8: All instances created successfully!")
sys.stdout.flush()

print("Step 9: Testing basic functionality...")
sys.stdout.flush()

# Create a simple mock RFP
mock_rfp = {
    'noticeId': 'TEST-001',
    'title': 'AI Development Services Test',
    'fullParentPathName': 'TEST AGENCY',
    'naicsCode': '541511',
    'classificationCode': 'D307',
    'description': 'Test RFP description for AI services.',
    'uiLink': 'https://sam.gov/test/1'
}

print("Step 10: Testing mini screening...")
sys.stdout.flush()

# Test mini screening
try:
    for_deep, maybe, rejected = mini_processor.process_batch([mock_rfp], threshold=4)
    print(f"Mini screening successful: {len(for_deep)} for deep analysis")
except Exception as e:
    print(f"Mini screening failed: {e}")

print("Step 11: All tests complete!")
sys.stdout.flush()