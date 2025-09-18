#!/usr/bin/env python3
"""
RFP Adder Channel Import Script
Sends import results directly to the rfp-adder channel
"""

import sys
import os
import requests
import json

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from import_rfp import RFPImporter

def send_to_rfp_adder(message):
    """Send message to rfp-adder channel webhook"""
    # You'll need to replace this with the actual webhook URL from the rfp-adder channel
    # Look for it in the incoming-webhook settings in that channel
    webhook_urls = [
        # Try known webhooks
        "https://hooks.slack.com/services/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",
        "https://hooks.slack.com/services/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",
    ]
    
    for webhook_url in webhook_urls:
        try:
            response = requests.post(webhook_url, json={"text": message})
            if response.status_code == 200:
                print(f"✅ Message sent to rfp-adder channel")
                return True
        except:
            continue
    
    print("❌ Could not send to rfp-adder channel - webhook URL needed")
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python rfp_adder_import.py <SAM.gov URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Validate URL
    if 'sam.gov' not in url:
        print("❌ Please provide a valid SAM.gov URL")
        print("Example: https://sam.gov/opp/a3069f8bfcc64e45b54558968b2c3094/view")
        sys.exit(1)
    
    print(f"🔄 Importing RFP from: {url}")
    
    # Send initial message to Slack
    send_to_rfp_adder(f"🔄 Processing import request...\nURL: {url}")
    
    # Run the import
    importer = RFPImporter()
    result = importer.import_rfp(url, user="rfp-adder")
    
    # Send result to Slack
    if result['success']:
        # Format success message
        message = f"✅ **RFP IMPORTED SUCCESSFULLY**\n\n{result['message']}"
    else:
        message = f"❌ **IMPORT FAILED**\n\n{result['message']}"
    
    send_to_rfp_adder(message)
    
    # Also print to console
    print(result['message'])
    
    sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()