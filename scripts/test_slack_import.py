#!/usr/bin/env python3
"""
Test Slack Import Integration
Simulates what happens when someone uses /import-rfp command
"""

import sys
import os
import requests

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import_via_webhook(sam_url, webhook_url):
    """Test importing an RFP and sending result to Slack"""
    
    print(f"Testing import for: {sam_url}")
    print(f"Will send results to webhook: {webhook_url[:50]}...")
    
    # First, send a message that we're starting
    message = {
        "text": "🔄 Testing RFP import functionality...",
        "attachments": [{
            "color": "warning",
            "fields": [
                {"title": "URL", "value": sam_url, "short": False},
                {"title": "Status", "value": "Processing...", "short": True}
            ]
        }]
    }
    
    response = requests.post(webhook_url, json=message)
    if response.status_code == 200:
        print("✅ Initial message sent to Slack")
    else:
        print(f"❌ Failed to send to Slack: {response.status_code}")
        return
    
    # Now run the actual import
    from scripts.import_rfp import RFPImporter
    
    importer = RFPImporter()
    result = importer.import_rfp(sam_url, user="SlackTest")
    
    # Send the result to Slack
    if result['success']:
        color = "good"
        emoji = "✅"
    else:
        color = "danger"
        emoji = "❌"
    
    final_message = {
        "text": f"{emoji} Import {'Completed' if result['success'] else 'Failed'}",
        "attachments": [{
            "color": color,
            "text": result['message'],
            "footer": "RFP Import System",
            "ts": int(time.time())
        }]
    }
    
    response = requests.post(webhook_url, json=final_message)
    if response.status_code == 200:
        print("✅ Result sent to Slack successfully")
    else:
        print(f"❌ Failed to send result: {response.status_code}")
    
    print("\nFull result:")
    print(result['message'])

if __name__ == "__main__":
    import time
    
    # Example SAM.gov URL - you can change this to test with a real one
    test_url = "https://sam.gov/opp/0ac2024aeef3471c854b3c1026c56f41/view"
    
    # The webhook URL - using the working obituary channel webhook
    # (The main channel webhook B09E6PZTNLS seems to be broken)
    webhook_url = "https://hooks.slack.com/services/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"
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    test_import_via_webhook(test_url, webhook_url)