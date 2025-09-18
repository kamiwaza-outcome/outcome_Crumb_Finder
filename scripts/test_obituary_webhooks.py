#!/usr/bin/env python3
"""
Test script to debug which webhook the obituary workflow is actually using
Run this with the same environment variables as the GitHub workflow
"""

import os
import sys
import json

def main():
    print("="*80)
    print("OBITUARY WEBHOOK CONFIGURATION TEST")
    print("="*80)
    
    # Check all relevant environment variables
    env_vars = {
        'SLACK_WEBHOOK_URL': os.getenv('SLACK_WEBHOOK_URL', 'NOT SET'),
        'SLACK_WEBHOOK_URL_2': os.getenv('SLACK_WEBHOOK_URL_2', 'NOT SET'),
        'SLACK_OBITUARY_WEBHOOK_URL': os.getenv('SLACK_OBITUARY_WEBHOOK_URL', 'NOT SET'),
    }
    
    print("\n📋 ENVIRONMENT VARIABLES:")
    print("-" * 40)
    for key, value in env_vars.items():
        if value != 'NOT SET':
            # Mask the webhook token for security
            if 'hooks.slack.com' in value:
                parts = value.split('/')
                webhook_id = parts[-2] if len(parts) > 2 else 'UNKNOWN'
                masked = f".../{webhook_id}/[MASKED]"
            else:
                masked = value[:20] + "..." if len(value) > 20 else value
            print(f"{key}: {masked}")
        else:
            print(f"{key}: {value}")
    
    print("\n🔍 WEBHOOK IDENTIFICATION:")
    print("-" * 40)
    
    # Identify which webhook IDs we have
    for key, value in env_vars.items():
        if value != 'NOT SET' and 'hooks.slack.com' in value:
            if 'B09E6PZTNLS' in value:
                print(f"  {key} = B09E6PZTNLS (Main channel webhook)")
            elif 'B09DS5T7BGX' in value:
                print(f"  {key} = B09DS5T7BGX (Obituary channel webhook)")
            else:
                print(f"  {key} = Unknown webhook ID")
    
    print("\n🎯 WHAT THE SCRIPT WILL USE:")
    print("-" * 40)
    
    # Import Config to see what it actually uses
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config
    
    # Check what Config provides
    config_webhooks = {
        'Config.SLACK_WEBHOOK_URL': getattr(Config, 'SLACK_WEBHOOK_URL', 'NOT SET'),
        'Config.SLACK_OBITUARY_WEBHOOK_URL': getattr(Config, 'SLACK_OBITUARY_WEBHOOK_URL', 'NOT SET'),
    }
    
    print("Config values:")
    for key, value in config_webhooks.items():
        if value and value != 'NOT SET' and 'hooks.slack.com' in value:
            parts = value.split('/')
            webhook_id = parts[-2] if len(parts) > 2 else 'UNKNOWN'
            print(f"  {key}: .../{webhook_id}/...")
        else:
            print(f"  {key}: {value}")
    
    # Show what rfp_obituary.py would use
    print("\n📌 OBITUARY SCRIPT LOGIC:")
    print("-" * 40)
    
    obituary_webhook = Config.SLACK_OBITUARY_WEBHOOK_URL if hasattr(Config, 'SLACK_OBITUARY_WEBHOOK_URL') and Config.SLACK_OBITUARY_WEBHOOK_URL else Config.SLACK_WEBHOOK_URL
    
    if obituary_webhook and 'hooks.slack.com' in obituary_webhook:
        parts = obituary_webhook.split('/')
        webhook_id = parts[-2] if len(parts) > 2 else 'UNKNOWN'
        print(f"Obituary will use: .../{webhook_id}/...")
        
        if 'B09E6PZTNLS' in obituary_webhook:
            print("  ⚠️  This is the MAIN channel webhook!")
        elif 'B09DS5T7BGX' in obituary_webhook:
            print("  ✅ This is the OBITUARY channel webhook (correct)")
        else:
            print("  ❓ Unknown webhook")
    else:
        print("No webhook configured!")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    
    # Check for issues
    issues = []
    
    if env_vars['SLACK_OBITUARY_WEBHOOK_URL'] == 'NOT SET':
        issues.append("SLACK_OBITUARY_WEBHOOK_URL is not set in environment")
        issues.append("The workflow should set: SLACK_OBITUARY_WEBHOOK_URL=${{ secrets.SLACK_WEBHOOK_URL_2 }}")
    
    if env_vars['SLACK_WEBHOOK_URL_2'] != 'NOT SET' and 'B09E6PZTNLS' in env_vars['SLACK_WEBHOOK_URL_2']:
        issues.append("SLACK_WEBHOOK_URL_2 contains the MAIN webhook, not obituary!")
        issues.append("You need to swap the secrets in GitHub settings")
    
    if obituary_webhook and 'B09E6PZTNLS' in obituary_webhook:
        issues.append("The obituary script is using the MAIN channel webhook!")
    
    if issues:
        print("❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  • {issue}")
    else:
        print("✅ Configuration looks correct!")
    
    print("\n📝 GitHub Secrets should be:")
    print("  • SLACK_WEBHOOK_URL = Main channel webhook (B09E6PZTNLS)")
    print("  • SLACK_WEBHOOK_URL_2 = Obituary channel webhook (B09DS5T7BGX)")

if __name__ == "__main__":
    main()