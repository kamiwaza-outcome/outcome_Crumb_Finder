#!/usr/bin/env python3
"""
Simple Slack to GitHub Actions Bridge
Receives Slack slash commands and triggers GitHub Actions
"""

import os
import json
import hashlib
import hmac
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Configuration
SLACK_SIGNING_SECRET = '600fb918d9f04ebf6199b3e6ff8de39a'  # From your screenshot
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # You'll need to set this
GITHUB_REPO = 'finnegannorris/Crumb_finder'

class SlackCommandHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests from Slack"""
        
        if self.path != '/slack/commands':
            self.send_response(404)
            self.end_headers()
            return
        
        # Read the request body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Verify Slack signature
        timestamp = self.headers.get('X-Slack-Request-Timestamp', '')
        slack_signature = self.headers.get('X-Slack-Signature', '')
        
        if not self.verify_signature(timestamp, slack_signature, post_data):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Invalid signature')
            return
        
        # Parse the form data
        data = parse_qs(post_data)
        command = data.get('command', [''])[0]
        text = data.get('text', [''])[0]
        user = data.get('user_name', ['Unknown'])[0]
        response_url = data.get('response_url', [''])[0]
        
        # Handle /import-rfp command
        if command == '/import-rfp':
            if not text or 'sam.gov/opp/' not in text:
                response = {
                    "text": "❌ Please provide a valid SAM.gov URL\nUsage: `/import-rfp https://sam.gov/opp/[noticeId]/view`",
                    "response_type": "ephemeral"
                }
            else:
                # Trigger GitHub Actions workflow
                self.trigger_github_action(command, text, user, response_url)
                response = {
                    "text": "✅ Import request received. Processing...",
                    "response_type": "ephemeral"
                }
        else:
            response = {
                "text": f"❌ Unknown command: {command}",
                "response_type": "ephemeral"
            }
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def verify_signature(self, timestamp, slack_signature, body):
        """Verify the request signature from Slack"""
        if abs(time.time() - float(timestamp)) > 60 * 5:
            return False
        
        sig_basestring = f"v0:{timestamp}:{body}"
        my_signature = 'v0=' + hmac.new(
            SLACK_SIGNING_SECRET.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(my_signature, slack_signature)
    
    def trigger_github_action(self, command, text, user, response_url):
        """Trigger GitHub Actions workflow"""
        if not GITHUB_TOKEN:
            print("Warning: GITHUB_TOKEN not set, cannot trigger workflow")
            return
        
        url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "event_type": "slack-command",
            "client_payload": {
                "command": command,
                "text": text,
                "user": user,
                "response_url": response_url
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 204:
                print(f"Successfully triggered GitHub Action for {command}")
            else:
                print(f"Failed to trigger GitHub Action: {response.status_code}")
        except Exception as e:
            print(f"Error triggering GitHub Action: {e}")
    
    def log_message(self, format, *args):
        """Suppress log messages"""
        pass

def run_server(port=3000):
    """Run the webhook server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, SlackCommandHandler)
    print(f"Slack webhook bridge running on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    run_server(port)