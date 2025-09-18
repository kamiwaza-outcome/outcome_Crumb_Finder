#!/usr/bin/env python3
"""
Test both Slack webhooks to identify which channel each goes to
"""

import requests
import json
import time

def test_webhook(webhook_url: str, message: str):
    """Send a test message to a webhook"""
    payload = {
        "text": message,
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🧪 Webhook Test",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Webhook ID: `{webhook_url.split('/')[-2]}`"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print(f"✅ Success: {message}")
            print(f"   Webhook: .../{webhook_url.split('/')[-2]}/...")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    print("="*60)
    print("TESTING SLACK WEBHOOKS")
    print("="*60)
    
    # Webhook 1: Main channel (supposedly)
    webhook1 = "https://hooks.slack.com/services/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"
    print("\n📨 Testing Webhook 1 (B09E6PZTNLS - supposed to be MAIN channel)...")
    test_webhook(webhook1, "🔵 TEST 1: This is the MAIN webhook (B09E6PZTNLS) - Should go to main RFP channel")
    
    # Wait a bit between messages
    time.sleep(2)
    
    # Webhook 2: Obituary channel (supposedly)
    webhook2 = "https://hooks.slack.com/services/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"
    print("\n📨 Testing Webhook 2 (B09DS5T7BGX - supposed to be OBITUARY channel)...")
    test_webhook(webhook2, "🟣 TEST 2: This is the OBITUARY webhook (B09DS5T7BGX) - Should go to obituary channel")
    
    print("\n" + "="*60)
    print("CHECK YOUR SLACK CHANNELS!")
    print("="*60)
    print("Please check which channels received which messages.")
    print("\nWebhook mapping:")
    print("  • B09E6PZTNLS = Webhook 1 (supposed to be main)")
    print("  • B09DS5T7BGX = Webhook 2 (supposed to be obituary)")
    print("\nIf they're reversed, we need to swap them in the code!")

if __name__ == "__main__":
    main()