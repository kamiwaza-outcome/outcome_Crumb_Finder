#!/usr/bin/env python3
"""Direct test of SAM.gov API"""

import requests
from datetime import datetime, timedelta

# Your API key
API_KEY = "KXHzDyofJ8WQXz5JuPt4Y3oNiYmFOx3803lqnbrs"

def test_sam_api():
    print("Testing SAM.gov API directly...")
    
    # Use proper date format and recent dates
    # SAM.gov dates should be in MM/DD/YYYY format
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    # Format dates
    date_from = week_ago.strftime('%m/%d/%Y')
    date_to = today.strftime('%m/%d/%Y')
    
    print(f"Date range: {date_from} to {date_to}")
    
    # SAM.gov API endpoint
    url = "https://api.sam.gov/opportunities/v2/search"
    
    # Parameters for the search
    params = {
        'api_key': API_KEY,
        'postedFrom': date_from,
        'postedTo': date_to,
        'limit': 10,
        'offset': 0,
        'ptype': 'o',  # Opportunities only
        'q': 'software'  # Simple keyword search
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Parameters: {params}")
    
    try:
        print("\nMaking request...")
        response = requests.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('totalRecords', 0)
            opportunities = data.get('opportunitiesData', [])
            
            print(f"\n✅ SUCCESS!")
            print(f"Total records found: {total}")
            print(f"Opportunities in response: {len(opportunities)}")
            
            if opportunities:
                print("\nFirst opportunity:")
                opp = opportunities[0]
                print(f"  Title: {opp.get('title', 'N/A')[:80]}")
                print(f"  Agency: {opp.get('fullParentPathName', 'N/A')}")
                print(f"  Posted: {opp.get('postedDate', 'N/A')}")
                print(f"  Notice ID: {opp.get('noticeId', 'N/A')}")
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sam_api()