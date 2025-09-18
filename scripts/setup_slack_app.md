# Setup Instructions for rfp-adder Channel

## Step 1: Add Your App to the Workspace and Channel

1. Go to: https://api.slack.com/apps/A09E7GEV7EW
2. Click **"Install App"** in the left sidebar
3. Click **"Install to Workspace"** (or "Reinstall" if already installed)
4. Authorize the permissions
5. After installation, go to your Slack workspace
6. In the #rfp-adder channel, type: `/invite @[your-app-name]`

## Step 2: Configure Slash Commands

1. Back in the Slack App settings (https://api.slack.com/apps/A09E7GEV7EW)
2. Click **"Slash Commands"** in the left sidebar
3. Click **"Create New Command"**
4. Configure:
   - Command: `/import-rfp`
   - Request URL: `https://your-endpoint.com/slack/commands` (see Step 3)
   - Short Description: `Import an RFP from SAM.gov`
   - Usage Hint: `[SAM.gov URL]`
   - Click **"Save"**

## Step 3: Set Up the Endpoint (Choose One Option)

### Option A: Use Pipedream (FREE & FASTEST)

1. Go to https://pipedream.com
2. Create a free account
3. Create a new workflow:
   - Trigger: HTTP / Webhook
   - Copy the endpoint URL (looks like: https://[random].m.pipedream.net)
4. Add this code to the workflow:

```javascript
export default defineComponent({
  async run({ steps, $ }) {
    const { text, user_name, response_url } = steps.trigger.event.body;
    
    // Trigger GitHub Actions
    await $.send.http({
      method: "POST",
      url: "https://api.github.com/repos/finnegannorris/Crumb_finder/dispatches",
      headers: {
        "Authorization": "token YOUR_GITHUB_TOKEN",
        "Accept": "application/vnd.github.v3+json"
      },
      data: {
        "event_type": "slack-import",
        "client_payload": {
          "url": text,
          "user": user_name,
          "response_url": response_url
        }
      }
    });
    
    // Return immediate response to Slack
    return {
      status: 200,
      body: {
        text: "Processing import request..."
      }
    };
  }
});
```

5. Use the Pipedream URL as your Request URL in the Slack command

### Option B: Use Zapier (Alternative)

1. Create a Zap with:
   - Trigger: Webhooks by Zapier → Catch Hook
   - Action: GitHub → Create Repository Dispatch

### Option C: Direct GitHub Integration

Since GitHub Actions can't receive webhooks directly from Slack, you need a bridge.

## Step 4: Configure OAuth & Permissions

1. In your Slack app settings, go to **"OAuth & Permissions"**
2. Add these Bot Token Scopes:
   - `commands` - To receive slash commands
   - `chat:write` - To send messages
   - `channels:read` - To see channel info
   - `incoming-webhook` - To post via webhooks
3. Click **"Install to Workspace"** again to update permissions

## Step 5: Add to rfp-adder Channel

In Slack, in the #rfp-adder channel:
1. Click the channel name at the top
2. Click "Integrations" 
3. Click "Add an App"
4. Find your app and click "Add"

## Step 6: Test

In the #rfp-adder channel, type:
```
/import-rfp https://sam.gov/opp/a3069f8bfcc64e45b54558968b2c3094/view
```

## Current Status

- ✅ App created (A09E7GEV7EW)
- ✅ Signing secret configured
- ❌ Slash command not configured (needs Request URL)
- ❌ App not installed to workspace
- ❌ App not added to #rfp-adder channel

The incoming-webhook you see in the channel is different from your app. You need to complete the steps above to get your app working with slash commands.