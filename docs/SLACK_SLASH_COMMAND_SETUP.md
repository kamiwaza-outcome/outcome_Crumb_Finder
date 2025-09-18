# Setting Up Slack Slash Commands for RFP Import

## Prerequisites
You have a Slack App with:
- App ID: `A09E7GEV7EW`
- Signing Secret: `600fb918d9f04ebf6199b3e6ff8de39a`
- Verification Token: `1xAFrq3wvqdxQoQn14IGRo6y`

## Step 1: Configure Slash Command in Slack

1. Go to https://api.slack.com/apps/A09E7GEV7EW
2. Click on **"Slash Commands"** in the left sidebar
3. Click **"Create New Command"**
4. Fill in:
   - **Command**: `/import-rfp`
   - **Request URL**: You'll need one of these options:
     - A public server URL (if you have one)
     - A service like ngrok for local testing
     - GitHub Actions webhook endpoint
   - **Short Description**: `Import an RFP from SAM.gov`
   - **Usage Hint**: `[SAM.gov URL]`

## Step 2: Choose Your Integration Method

### Option A: Direct Script Execution (Simplest for Testing)

Since you don't have a public server, you can manually run imports:

```bash
# Test with the webhook
python scripts/test_slack_import.py "https://sam.gov/opp/YOUR_NOTICE_ID/view"
```

### Option B: Using GitHub Actions (Recommended)

1. Create a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Generate new token with `repo` scope
   - Save it as `GITHUB_TOKEN`

2. Set up a webhook receiver (you'll need a service like):
   - **Pipedream**: https://pipedream.com (FREE)
   - **Zapier**: https://zapier.com
   - **IFTTT**: https://ifttt.com

3. Configure the webhook to trigger GitHub Actions

### Option C: Local Testing with ngrok

1. Install ngrok: `brew install ngrok` (on Mac)
2. Run the webhook bridge:
   ```bash
   python scripts/slack_webhook_bridge.py
   ```
3. Expose it with ngrok:
   ```bash
   ngrok http 3000
   ```
4. Use the ngrok URL as your Request URL in Slack

## Step 3: Test the Command

In any Slack channel:
```
/import-rfp https://sam.gov/opp/0ac2024aeef3471c854b3c1026c56f41/view
```

## Manual Import (Current Working Method)

While setting up the slash command, you can manually import RFPs:

```bash
# Run directly
python scripts/import_rfp.py "https://sam.gov/opp/NOTICE_ID/view"

# Send result to Slack webhook
python scripts/test_slack_import.py "https://sam.gov/opp/NOTICE_ID/view"
```

## Webhook URL for Testing

Your webhook URL that's currently working:
```
https://hooks.slack.com/services/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
```

This can receive messages but cannot handle slash commands directly.

## Quick Test

Test if your webhook is working:
```bash
curl -X POST https://hooks.slack.com/services/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 \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test message from RFP Import System"}'
```

## Troubleshooting

1. **"Command not found"**: Make sure you saved the slash command in Slack
2. **"Invalid URL"**: The Request URL must be publicly accessible
3. **No response**: Check that your handler is running and accessible

## Next Steps

For a production setup, consider:
1. Using AWS Lambda or Google Cloud Functions
2. Setting up a dedicated server
3. Using a service like Pipedream to bridge Slack to GitHub Actions