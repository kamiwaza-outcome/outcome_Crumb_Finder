#!/usr/bin/env python3
"""
Test your Slack webhook URL
This script helps verify your Slack integration is working
"""

import requests
import json
from datetime import datetime

def test_simple_message(webhook_url):
    """Send a simple test message"""
    message = {
        "text": "✅ Webhook test successful! Your RFP Discovery Bot is connected."
    }
    
    response = requests.post(webhook_url, json=message)
    return response.status_code == 200

def test_rich_message(webhook_url):
    """Send a rich formatted message like the bot would"""
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎯 RFP Discovery Bot Test",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Test Time:* {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n*Status:* ✅ Webhook configured successfully!"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Feature:*\nRFP Import"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:*\n✅ Ready"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Feature:*\nDaily Discovery"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:*\n✅ Ready"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Feature:*\nWeekly Obituary"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:*\n✅ Ready"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🤖 Your RFP Discovery Bot is now connected to this channel!"
                    }
                ]
            }
        ],
        "text": "RFP Discovery Bot Test - Webhook configured successfully!"
    }
    
    response = requests.post(webhook_url, json=message)
    return response.status_code == 200

def test_import_preview(webhook_url):
    """Send a preview of what an import notification would look like"""
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📥 Example: RFP Import Notification",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*This is what you'll see when someone imports an RFP:*"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Title:*\nCloud Infrastructure Modernization"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Agency:*\nGeneral Services Administration"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Deadline:*\nFebruary 15, 2025"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*AI Score:*\nImported (Originally 8/10)"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ *Successfully imported to Main Sheet (Row 247)*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Sheet",
                            "emoji": True
                        },
                        "url": "https://docs.google.com/spreadsheets/d/example",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Open Drive Folder",
                            "emoji": True
                        },
                        "url": "https://drive.google.com/example"
                    }
                ]
            }
        ],
        "text": "Example RFP Import Notification"
    }
    
    response = requests.post(webhook_url, json=message)
    return response.status_code == 200

def main():
    print("=" * 60)
    print("SLACK WEBHOOK TEST")
    print("=" * 60)
    print()
    
    print("Follow these steps to get your webhook URL:")
    print("1. Go to https://api.slack.com/apps")
    print("2. Create a new app or select existing 'RFP Discovery Bot'")
    print("3. Click 'Incoming Webhooks' in the left menu")
    print("4. Turn ON the feature")
    print("5. Click 'Add New Webhook to Workspace'")
    print("6. Choose a channel and click Allow")
    print("7. Copy the webhook URL")
    print()
    
    webhook_url = input("Paste your Slack webhook URL here: ").strip()
    
    if not webhook_url or not webhook_url.startswith("https://hooks.slack.com/"):
        print("❌ Invalid webhook URL. It should start with https://hooks.slack.com/")
        return
    
    print()
    print("Testing webhook...")
    print()
    
    # Test 1: Simple message
    print("1. Sending simple test message...")
    if test_simple_message(webhook_url):
        print("   ✅ Simple message sent successfully!")
    else:
        print("   ❌ Failed to send simple message")
        return
    
    # Test 2: Rich message
    print("2. Sending rich formatted message...")
    if test_rich_message(webhook_url):
        print("   ✅ Rich message sent successfully!")
    else:
        print("   ❌ Failed to send rich message")
    
    # Test 3: Import preview
    print("3. Sending import notification preview...")
    if test_import_preview(webhook_url):
        print("   ✅ Import preview sent successfully!")
    else:
        print("   ❌ Failed to send import preview")
    
    print()
    print("=" * 60)
    print("✅ WEBHOOK TEST COMPLETE!")
    print("=" * 60)
    print()
    print("Your webhook URL is working! Now you need to:")
    print()
    print("1. ADD TO LOCAL ENVIRONMENT:")
    print(f"   export SLACK_WEBHOOK_URL='{webhook_url}'")
    print()
    print("2. ADD TO .env FILE (if using):")
    print(f"   SLACK_WEBHOOK_URL={webhook_url}")
    print()
    print("3. ADD TO GITHUB SECRETS:")
    print("   - Go to your repo settings")
    print("   - Click Secrets and variables > Actions")
    print("   - Click 'New repository secret'")
    print("   - Name: SLACK_WEBHOOK_URL")
    print(f"   - Value: {webhook_url}")
    print()
    print("Check your Slack channel - you should see 3 test messages!")

if __name__ == "__main__":
    main()