#!/usr/bin/env python3
"""Test concurrency to see if that's where the hang occurs"""

import sys
import time
from dotenv import load_dotenv

load_dotenv()

from config import Config
from parallel_mini_processor import ParallelMiniProcessor

def generate_small_mock_rfps(count=5):
    """Generate a small set of mock RFPs for testing"""
    rfps = []
    for i in range(count):
        rfps.append({
            'noticeId': f'TEST-{i:03d}',
            'title': f'AI Development Services Test #{i}',
            'fullParentPathName': 'TEST AGENCY',
            'naicsCode': '541511',
            'classificationCode': 'D307',
            'description': f'Test RFP description for AI services #{i}.',
            'uiLink': f'https://sam.gov/test/{i}'
        })
    return rfps

print("Creating mock RFPs...")
mock_rfps = generate_small_mock_rfps(5)

print("Creating ParallelMiniProcessor with high concurrency...")
mini_processor = ParallelMiniProcessor(
    Config.OPENAI_API_KEY, 
    max_concurrent=200  # This is the suspected culprit
)

print("Starting parallel processing...")
try:
    for_deep, maybe, rejected = mini_processor.process_batch(mock_rfps, threshold=4)
    print(f"Success! Results: {len(for_deep)} for deep, {len(maybe)} maybe, {len(rejected)} rejected")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()

print("Test complete!")