#!/usr/bin/env python3
"""
Slack Webhook Handler for RFP Import Commands
This script handles incoming Slack slash commands and triggers GitHub Actions
"""

import os
import json
import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify
from urllib.parse import parse_qs
import logging

# For local testing, you can also use ngrok and run this locally
# pip install flask
# python slack_webhook_handler.py

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')  # From Slack app settings
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # GitHub personal access token
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Crumb_finder')  # Your repo name
GITHUB_OWNER = os.getenv('GITHUB_OWNER')  # Your GitHub username

def verify_slack_request(request):
    """Verify that the request actually came from Slack"""
    if not SLACK_SIGNING_SECRET:
        logger.warning("No SLACK_SIGNING_SECRET configured, skipping verification")
        return True
    
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    
    if not timestamp or not signature:
        return False
    
    # Check timestamp is recent (within 5 minutes)
    if abs(time.time() - float(timestamp)) > 300:
        return False
    
    # Build the signature base string
    sig_basestring = f"v0:{timestamp}:{request.get_data().decode('utf-8')}"
    
    # Calculate expected signature
    my_signature = 'v0=' + hmac.new(
        bytes(SLACK_SIGNING_SECRET, 'utf-8'),
        bytes(sig_basestring, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(my_signature, signature)

def trigger_github_action(url, user, response_url):
    """Trigger the GitHub Action workflow"""
    
    github_api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/import-rfp.yml/dispatches"
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'ref': 'main',  # or your default branch
        'inputs': {
            'url': url,
            'user': user,
            'slack_response_url': response_url
        }
    }
    
    try:
        response = requests.post(github_api_url, headers=headers, json=payload)
        response.raise_for_status()
        return True, "Workflow triggered successfully"
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to trigger GitHub Action: {str(e)}")
        return False, f"Failed to trigger workflow: {str(e)}"

@app.route('/slack/commands/import-rfp', methods=['POST'])
def handle_import_rfp():
    """Handle the /import-rfp slash command from Slack"""
    
    # Verify the request is from Slack
    if not verify_slack_request(request):
        return jsonify({'error': 'Invalid request signature'}), 403
    
    # Parse the form data from Slack
    data = parse_qs(request.get_data().decode('utf-8'))
    
    command = data.get('command', [''])[0]
    text = data.get('text', [''])[0].strip()
    user_name = data.get('user_name', ['Unknown'])[0]
    response_url = data.get('response_url', [''])[0]
    
    # Validate the command
    if command != '/import-rfp':
        return jsonify({'text': '❌ Unknown command'}), 200
    
    # Validate the URL
    if not text:
        return jsonify({
            'text': '❌ Please provide a SAM.gov URL\nUsage: `/import-rfp https://sam.gov/opp/{noticeId}/view`'
        }), 200
    
    if 'sam.gov/opp/' not in text:
        return jsonify({
            'text': '❌ Invalid URL. Please provide a valid SAM.gov opportunity URL\nExample: `https://sam.gov/opp/abc123/view`'
        }), 200
    
    # Send immediate response to Slack (must respond within 3 seconds)
    immediate_response = {
        'text': f'🔄 Processing import request from {user_name}...\nURL: {text}\n\nThis may take 30-60 seconds. Results will appear here when complete.'
    }
    
    # Trigger the GitHub Action
    success, message = trigger_github_action(text, user_name, response_url)
    
    if not success:
        # If we can't trigger the action, update the message
        requests.post(response_url, json={
            'text': f'❌ Failed to start import process: {message}\nPlease contact Finn for assistance.'
        })
        return jsonify(immediate_response), 200
    
    # Return immediate response
    return jsonify(immediate_response), 200

@app.route('/slack/commands/check-rfp', methods=['POST'])
def handle_check_rfp():
    """Handle the /check-rfp slash command to check if an RFP is already tracked"""
    
    # Verify the request is from Slack
    if not verify_slack_request(request):
        return jsonify({'error': 'Invalid request signature'}), 403
    
    # Parse the form data
    data = parse_qs(request.get_data().decode('utf-8'))
    text = data.get('text', [''])[0].strip()
    
    if not text:
        return jsonify({
            'text': '❌ Please provide a SAM.gov URL or notice ID\nUsage: `/check-rfp https://sam.gov/opp/{noticeId}/view`'
        }), 200
    
    # For now, return a message that this feature is coming soon
    # In production, this would query the sheets to check if the RFP exists
    return jsonify({
        'text': '🔍 Check RFP feature coming soon!\nFor now, use `/import-rfp` which will tell you if the RFP already exists.'
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    # For local testing only
    # In production, deploy this to AWS Lambda, Google Cloud Functions, or a web server
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)