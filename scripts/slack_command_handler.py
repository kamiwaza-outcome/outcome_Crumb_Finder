#!/usr/bin/env python3
"""
Slack Command Handler for /import-rfp
Receives slash commands and triggers RFP import
"""

import os
import sys
import json
import hashlib
import hmac
import time
import subprocess
import threading
from flask import Flask, request, jsonify
from urllib.parse import parse_qs

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# Your Slack app's signing secret (from the screenshot)
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET', '600fb918d9f04ebf6199b3e6ff8de39a')
SLACK_VERIFICATION_TOKEN = os.getenv('SLACK_VERIFICATION_TOKEN', '1xAFrq3wvqdxQoQn14IGRo6y')

def verify_slack_request(request):
    """Verify that the request came from Slack"""
    
    # Get request timestamp and signature
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    slack_signature = request.headers.get('X-Slack-Signature', '')
    
    # Check timestamp to prevent replay attacks
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False
    
    # Create the basestring
    sig_basestring = f"v0:{timestamp}:{request.get_data(as_text=True)}"
    
    # Create a new HMAC
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(my_signature, slack_signature)

def process_import_async(url, user, response_url):
    """Process the import in the background"""
    try:
        # Send immediate acknowledgment
        import requests
        requests.post(response_url, json={
            "text": f"🔄 Processing import for: {url}\nThis may take a minute..."
        })
        
        # Run the import script
        result = subprocess.run([
            sys.executable,
            'scripts/import_rfp.py',
            url,
            '--user', user
        ], capture_output=True, text=True)
        
        # Send the result back to Slack
        if result.returncode == 0:
            requests.post(response_url, json={
                "text": result.stdout,
                "response_type": "in_channel"
            })
        else:
            requests.post(response_url, json={
                "text": f"❌ Import failed: {result.stderr}",
                "response_type": "ephemeral"
            })
            
    except Exception as e:
        import requests
        requests.post(response_url, json={
            "text": f"❌ Error: {str(e)}",
            "response_type": "ephemeral"
        })

@app.route('/slack/commands', methods=['POST'])
def handle_command():
    """Handle incoming slash commands from Slack"""
    
    # Verify the request is from Slack
    if not verify_slack_request(request):
        return jsonify({"error": "Invalid request signature"}), 403
    
    # Parse the command data
    data = request.form
    command = data.get('command')
    text = data.get('text', '').strip()
    user_name = data.get('user_name', 'Unknown')
    response_url = data.get('response_url')
    
    # Handle /import-rfp command
    if command == '/import-rfp':
        if not text:
            return jsonify({
                "text": "❌ Please provide a SAM.gov URL\nUsage: `/import-rfp https://sam.gov/opp/[noticeId]/view`",
                "response_type": "ephemeral"
            })
        
        # Validate URL format
        if 'sam.gov/opp/' not in text:
            return jsonify({
                "text": "❌ Invalid URL format\nExpected: `https://sam.gov/opp/[noticeId]/view`",
                "response_type": "ephemeral"
            })
        
        # Process the import asynchronously
        thread = threading.Thread(
            target=process_import_async,
            args=(text, user_name, response_url)
        )
        thread.start()
        
        # Return immediate response
        return jsonify({
            "text": f"✅ Import request received from {user_name}",
            "response_type": "ephemeral"
        })
    
    # Handle /check-rfp command
    elif command == '/check-rfp':
        if not text:
            return jsonify({
                "text": "❌ Please provide a SAM.gov URL\nUsage: `/check-rfp https://sam.gov/opp/[noticeId]/view`",
                "response_type": "ephemeral"
            })
        
        # Extract notice ID and check if it exists
        import re
        match = re.search(r'sam\.gov/opp/([^/]+)', text)
        if match:
            notice_id = match.group(1)
            # Quick check logic here
            return jsonify({
                "text": f"🔍 Checking for Notice ID: {notice_id}...",
                "response_type": "ephemeral"
            })
        else:
            return jsonify({
                "text": "❌ Could not extract Notice ID from URL",
                "response_type": "ephemeral"
            })
    
    # Unknown command
    return jsonify({
        "text": f"❌ Unknown command: {command}",
        "response_type": "ephemeral"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)