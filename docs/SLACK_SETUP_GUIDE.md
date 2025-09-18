# Complete Slack Integration Setup Guide

## Overview
Your RFP Discovery system already has Slack integration built-in but needs a webhook URL. This guide will walk you through:
1. Creating the webhook
2. Testing it locally
3. Adding it to GitHub
4. Setting up the import command

## Part 1: Create Your Slack Webhook (5 minutes)

### Option A: Quick Setup (Incoming Webhook Only)

1. **Go to**: https://slack.com/apps/A0F7XDUAZ-incoming-webhooks
2. **Click**: "Add to Slack"
3. **Choose Channel**: Select where RFP notifications should go (e.g., #rfp-tracking)
4. **Click**: "Add Incoming WebHooks integration"
5. **Copy**: The Webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`)
6. **Optional**: Customize the name to "RFP Discovery Bot" and add an icon

### Option B: Full App Setup (For Slash Commands Later)

1. **Go to**: https://api.slack.com/apps
2. **Click**: "Create New App" → "From scratch"
3. **Name**: "RFP Discovery Bot"
4. **Select**: Your workspace
5. **Enable Webhooks**:
   - Left menu → "Incoming Webhooks"
   - Toggle ON
   - "Add New Webhook to Workspace"
   - Choose channel
   - Copy the webhook URL

## Part 2: Test Your Webhook (2 minutes)

Run the test script I created:

```bash
cd /Users/finnegannorris/code/Crumb_finder
python test_slack_webhook.py
```

Follow the prompts and paste your webhook URL. You should see 3 test messages in Slack.

## Part 3: Configure Your Environment

### Local Testing
Add to your shell profile (`~/.zshrc` or `~/.bash_profile`):
```bash
export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
```

Then reload:
```bash
source ~/.zshrc  # or source ~/.bash_profile
```

### GitHub Actions
1. Go to: https://github.com/[YOUR_USERNAME]/Crumb_finder/settings/secrets/actions
2. Click: "New repository secret"
3. Add:
   - Name: `SLACK_WEBHOOK_URL`
   - Secret: Your webhook URL

## Part 4: Test Current Features

Once configured, these features will automatically work:

### 1. Daily RFP Discovery Notifications
- **When**: Every day at 8am Eastern
- **What**: New RFPs found and added to sheets
- **Test**: Run workflow manually in GitHub Actions

### 2. Weekly RFP Obituary
- **When**: Fridays at 5pm Eastern
- **What**: Humorous memorial for expired opportunities
- **Test**: Run with test mode in GitHub Actions

### 3. Manual Import (After Slash Command Setup)
- **Command**: `/import-rfp [SAM.gov URL]`
- **What**: Import specific RFPs team members find

## Part 5: Setting Up Slash Command for Import (Optional - 10 minutes)

Since you want the import feature, here's the simplest approach using GitHub Actions:

### Step 1: Create Slack Workflow
1. In Slack, click your workspace name → "Tools" → "Workflow Builder"
2. Create new workflow → "Start from scratch"
3. Name: "Import RFP"
4. **Trigger**: Choose "Shortcut"
5. **Add Form**:
   - Field name: "SAM.gov URL"
   - Variable: `sam_url`

### Step 2: Add GitHub Webhook
1. Add step → "Send a webhook"
2. URL: `https://api.github.com/repos/[YOUR_GITHUB_USERNAME]/Crumb_finder/actions/workflows/import-rfp.yml/dispatches`
3. Method: POST
4. Headers:
   ```json
   {
     "Authorization": "Bearer [YOUR_GITHUB_TOKEN]",
     "Accept": "application/vnd.github.v3+json"
   }
   ```
5. Body:
   ```json
   {
     "ref": "main",
     "inputs": {
       "url": "{{sam_url}}",
       "user": "{{person_who_started_workflow}}"
     }
   }
   ```

### Step 3: Create GitHub Token
1. Go to: https://github.com/settings/tokens
2. "Generate new token (classic)"
3. Name: "Slack RFP Import"
4. Scopes: Select `repo` and `workflow`
5. Generate and copy token

### Step 4: Test Import
1. In Slack, type `/workflow` and select your "Import RFP" workflow
2. Enter a SAM.gov URL
3. Check GitHub Actions to see it running
4. Check your Main sheet for the imported RFP

## Quick Test Commands

After setup, test each component:

```bash
# Test Slack connection
python test_slack_webhook.py

# Test RFP import locally
python test_import.py https://sam.gov/opp/[some-notice-id]/view

# Test obituary in test mode
python rfp_obituary.py --test --days 7
```

## Troubleshooting

### "No SLACK_WEBHOOK_URL configured"
- Ensure you've exported the environment variable
- Check it's in GitHub Secrets for Actions

### Messages not appearing in Slack
- Verify webhook URL is correct
- Check the channel still exists
- Ensure bot hasn't been removed from channel

### Import command not working
- Verify GitHub token has correct permissions
- Check workflow file exists in `.github/workflows/import-rfp.yml`
- Look at GitHub Actions logs for errors

## Current Status Check

Run this to verify your setup:

```bash
python -c "
from config import Config
import os

print('Checking Slack configuration...')
print('=' * 50)

# Check local environment
webhook = Config.SLACK_WEBHOOK_URL
if webhook:
    print(f'✅ Webhook configured: {webhook[:40]}...')
else:
    print('❌ No webhook found in environment')

# Check if webhook is just empty string
if os.getenv('SLACK_WEBHOOK_URL') == '':
    print('⚠️  SLACK_WEBHOOK_URL is set but empty')

print('=' * 50)
"
```

## Next Steps

1. **Immediate**: Set up the webhook URL (Part 1-3) - Takes 5 minutes
2. **Test**: Run the test script to verify it works
3. **Optional**: Set up slash command for imports (Part 5) - Takes 10 minutes
4. **Monitor**: Watch the daily runs and Friday obituaries

Once you have the webhook URL, all your existing features (daily discovery, weekly obituary) will start sending Slack notifications automatically!