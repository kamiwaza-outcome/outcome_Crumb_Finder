#!/usr/bin/env python
"""Test SAM.gov API connection"""

import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

from config import Config
from sam_client import SAMClient

def main():
    print("Testing SAM.gov API...")
    print(f"API Key present: {'Yes' if Config.SAM_API_KEY else 'No'}")
    print(f"API Key starts with: {Config.SAM_API_KEY[:10] if Config.SAM_API_KEY else 'NOT SET'}")
    
    # Test date - yesterday
    test_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
    print(f"\nTesting with date: {test_date}")
    
    # Initialize client
    sam_client = SAMClient(Config.SAM_API_KEY)
    
    # Try simple search
    try:
        print("\nAttempting basic search...")
        params = {
            'api_key': Config.SAM_API_KEY,
            'postedFrom': test_date,
            'postedTo': test_date,
            'limit': 5,
            'offset': 0,
            'active': 'true'
        }
        
        # Direct API call
        import requests
        response = requests.get(
            Config.SAM_BASE_URL,
            params=params,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('totalRecords', 0)
            opps = data.get('opportunitiesData', [])
            print(f"Total records: {total}")
            print(f"Retrieved: {len(opps)} opportunities")
            
            if opps:
                print(f"\nFirst RFP: {opps[0].get('title', 'NO TITLE')[:80]}")
        else:
            print(f"Error: {response.text[:500]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()