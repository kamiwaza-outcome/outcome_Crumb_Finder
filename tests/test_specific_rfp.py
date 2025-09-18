#!/usr/bin/env python3
"""
Test script to retrieve specific RFPs by notice ID from SAM.gov API
"""

import requests
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def get_specific_rfp(notice_id: str, days_back: int = 30):
    """
    Retrieve a specific RFP by its notice ID
    
    Args:
        notice_id: The SAM.gov notice ID
        days_back: How many days back to search (default 30)
    
    Returns:
        Dictionary with RFP data or None if not found
    """
    api_key = os.getenv('SAM_API_KEY')
    if not api_key:
        print("❌ No SAM_API_KEY found in environment")
        return None
    
    print(f"🔍 Searching for Notice ID: {notice_id}")
    
    # SAM.gov requires date range for searches
    base_url = 'https://api.sam.gov/opportunities/v2/search'
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%m/%d/%Y')
    end_date = datetime.now().strftime('%m/%d/%Y')
    
    params = {
        'api_key': api_key,
        'noticeId': notice_id,
        'postedFrom': start_date,
        'postedTo': end_date,
        'limit': 1
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('opportunitiesData') and len(data['opportunitiesData']) > 0:
                opp = data['opportunitiesData'][0]
                print(f"✅ Found: {opp.get('title', 'N/A')[:60]}...")
                return opp
            else:
                print(f"❌ No RFP found with notice ID: {notice_id}")
                print(f"   Searched from {start_date} to {end_date}")
                return None
        else:
            print(f"❌ API Error {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

def test_direct_endpoint(notice_id: str):
    """
    Test the direct opportunity endpoint (often returns 500 errors)
    """
    api_key = os.getenv('SAM_API_KEY')
    if not api_key:
        return None
    
    print(f"🔍 Testing direct endpoint for: {notice_id}")
    
    # Direct endpoint - often fails with 500 errors
    url = f'https://api.sam.gov/opportunities/v2/{notice_id}'
    params = {'api_key': api_key}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            print("✅ Direct endpoint worked!")
            return response.json()
        else:
            print(f"❌ Direct endpoint failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Direct endpoint exception: {str(e)}")
        return None

def print_rfp_details(rfp: dict):
    """Print formatted RFP details"""
    if not rfp:
        return
    
    print("\n" + "="*60)
    print("RFP DETAILS")
    print("="*60)
    
    print(f"\n📋 BASIC INFO")
    print(f"  Title: {rfp.get('title', 'N/A')}")
    print(f"  Notice ID: {rfp.get('noticeId', 'N/A')}")
    print(f"  Sol Number: {rfp.get('solicitationNumber', 'N/A')}")
    print(f"  Type: {rfp.get('type', 'N/A')}")
    
    print(f"\n📅 DATES")
    print(f"  Posted: {rfp.get('postedDate', 'N/A')}")
    print(f"  Response Deadline: {rfp.get('responseDeadLine', 'N/A')}")
    print(f"  Archive Date: {rfp.get('archiveDate', 'N/A')}")
    
    print(f"\n🏢 AGENCY")
    print(f"  Agency: {rfp.get('fullParentPathName', 'N/A')}")
    office = rfp.get('officeAddress', {})
    if office:
        print(f"  Location: {office.get('city', '')}, {office.get('state', '')} {office.get('zipcode', '')}")
    
    print(f"\n🏷️ CLASSIFICATION")
    print(f"  NAICS: {rfp.get('naicsCode', 'N/A')}")
    print(f"  PSC: {rfp.get('classificationCode', 'N/A')}")
    print(f"  Set Aside: {rfp.get('typeOfSetAside', 'N/A')}")
    
    print(f"\n📄 CONTENT")
    desc = rfp.get('description', '')
    if desc.startswith('http'):
        print(f"  Description: Link to external content")
        print(f"  URL: {desc}")
    else:
        print(f"  Description: {len(desc)} characters")
        if desc:
            print(f"  Preview: {desc[:200]}...")
    
    print(f"\n🔗 LINKS")
    print(f"  SAM.gov: {rfp.get('uiLink', 'N/A')}")
    
    if rfp.get('resourceLinks'):
        print(f"  Resource Links: {len(rfp['resourceLinks'])} available")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test with provided notice ID
        notice_id = sys.argv[1]
        print(f"Testing with provided notice ID: {notice_id}\n")
    else:
        # Test with a known recent notice ID
        notice_id = "ffc7d69492944cb499af62babcaa6ed8"
        print(f"Testing with default notice ID: {notice_id}\n")
    
    # Try direct endpoint first (usually fails)
    print("METHOD 1: Direct Endpoint")
    print("-" * 30)
    direct_result = test_direct_endpoint(notice_id)
    
    # Try search method (more reliable)
    print("\nMETHOD 2: Search API")
    print("-" * 30)
    search_result = get_specific_rfp(notice_id)
    
    # Print details if found
    if search_result:
        print_rfp_details(search_result)
        
        # Save to file for inspection
        filename = f"rfp_{notice_id[:8]}.json"
        with open(filename, 'w') as f:
            json.dump(search_result, f, indent=2)
        print(f"\n💾 Full data saved to {filename}")
    else:
        print("\n❌ Could not retrieve RFP data")
        print("\nPossible reasons:")
        print("1. Notice ID doesn't exist")
        print("2. RFP is older than search range (try increasing days_back)")
        print("3. RFP has been archived/removed")
        print("4. API key doesn't have proper permissions")