# Slack RFP Import Setup Guide

## Overview
This guide will help you set up the `/import-rfp` Slack command to import RFPs directly from SAM.gov URLs into your main tracking sheet.

## Setup Options

### Option 1: Using Slack Workflows + GitHub Actions (Recommended)

This is the simplest approach that doesn't require any external hosting.

#### Step 1: Create a Slack Workflow

1. In Slack, go to **Tools** → **Workflow Builder**
2. Click **Create Workflow**
3. Choose **Start from Scratch**
4. Name it "Import RFP"

#### Step 2: Configure the Workflow Trigger

1. Choose **Shortcut** as the trigger
2. Set the shortcut name: "Import RFP"
3. Add an input field:
   - Label: "SAM.gov URL"
   - Variable name: `sam_url`
   - Type: Text (single line)

#### Step 3: Add Webhook Step

1. Add a step → **Send a webhook**
2. Set the webhook URL to:
   ```
   https://api.github.com/repos/[YOUR_GITHUB_USERNAME]/Crumb_finder/dispatches
   ```
3. Set Headers:
   ```json
   {
     "Authorization": "Bearer [YOUR_GITHUB_TOKEN]",
     "Accept": "application/vnd.github.v3+json"
   }
   ```
4. Set Body:
   ```json
   {
     "event_type": "import-rfp",
     "client_payload": {
       "url": "{{sam_url}}",
       "user": "{{person_who_started_workflow}}",
       "channel": "{{channel_id}}"
     }
   }
   ```

#### Step 4: Add Response Message

1. Add a step → **Send a message**
2. Choose the channel where the workflow was triggered
3. Message text:
   ```
   🔄 Processing RFP import for {{person_who_started_workflow}}
   URL: {{sam_url}}
   
   Please wait 30-60 seconds for processing...
   ```

### Option 2: Direct Slash Command (Requires Hosting)

#### Step 1: Create Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From Scratch**
3. Name: "RFP Importer"
4. Choose your workspace

#### Step 2: Create Slash Command

1. In your app settings, go to **Slash Commands**
2. Click **Create New Command**
3. Command: `/import-rfp`
4. Request URL: `[YOUR_WEBHOOK_URL]/slack/commands/import-rfp`
5. Short Description: "Import an RFP from SAM.gov"
6. Usage Hint: `[SAM.gov URL]`

#### Step 3: Install App to Workspace

1. Go to **OAuth & Permissions**
2. Click **Install to Workspace**
3. Authorize the app

#### Step 4: Deploy Webhook Handler

Deploy `slack_webhook_handler.py` to one of:
- AWS Lambda (using API Gateway)
- Google Cloud Functions  
- Heroku
- Any web server with HTTPS

Set environment variables:
- `SLACK_SIGNING_SECRET`: From your Slack app's Basic Information
- `GITHUB_TOKEN`: Your GitHub personal access token
- `GITHUB_REPO`: Crumb_finder
- `GITHUB_OWNER`: Your GitHub username

### Option 3: Using Zapier/Make (No Code)

1. Create a Zap/Scenario that:
   - Triggers on a Slack message containing "import-rfp"
   - Extracts the URL from the message
   - Triggers the GitHub Action via API
   - Responds in Slack with the result

## GitHub Action Setup (Required for All Options)

### 1. Add GitHub Secrets

Go to your repository Settings → Secrets → Actions and add:
- `SLACK_WEBHOOK_URL`: Your Slack incoming webhook URL

### 2. Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` and `workflow` scopes
3. Save this token (you'll need it for the Slack webhook)

### 3. Update the GitHub Action

The `import-rfp.yml` workflow is already configured to handle:
- Direct `workflow_dispatch` triggers
- Repository dispatch events from webhooks

## Testing the Integration

### Test via GitHub UI:
1. Go to Actions → Import RFP from SAM.gov
2. Click "Run workflow"
3. Enter a SAM.gov URL
4. Check the main sheet for the imported RFP

### Test via Slack:
1. Type `/import-rfp https://sam.gov/opp/[notice-id]/view`
2. Wait for the confirmation message
3. Check the main sheet

## Troubleshooting

### Common Issues:

1. **"Invalid URL" error**
   - Ensure the URL follows the format: `https://sam.gov/opp/{noticeId}/view`

2. **"Already tracking" message**
   - The RFP already exists in the main sheet
   - Check the row number provided in the error message

3. **No response in Slack**
   - Check GitHub Actions logs for errors
   - Verify all secrets are configured correctly
   - Ensure the GitHub token has proper permissions

4. **Import succeeds but shows "Imported" instead of score**
   - This is expected behavior for manual imports
   - The actual AI score is calculated but hidden
   - Contact Finn if you think the AI filtering is incorrect

## Usage Examples

### Basic Import:
```
/import-rfp https://sam.gov/opp/abc123def456/view
```

### Response Format:
```
✅ IMPORTED TO MAIN SHEET
Row: 247 | Status: Active

📋 RFP DETAILS
Title: Defense Logistics IT Modernization
Agency: Department of Defense
Deadline: 2025-02-15
...

🤖 AI ASSESSMENT
Score: Imported (AI rated 8/10)

📁 RESOURCES
SAM.gov: [link]
Drive Folder: [link]
Sheet Row: [link]
```

## Support

If you encounter issues or need help:
1. Check the GitHub Actions logs
2. Verify all credentials and secrets
3. Contact Finn for assistance with AI scoring adjustments