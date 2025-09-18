// Pipedream Workflow for Slack /import-rfp Command
// This handles the slash command and sends the import request to your webhook

export default defineComponent({
  async run({ steps, $ }) {
    // Parse the Slack command data
    const { 
      text,           // The URL provided after /import-rfp
      user_name,      // Who ran the command
      channel_name,   // Which channel (should be rfp-adder)
      response_url,   // URL to send delayed responses
      team_domain
    } = steps.trigger.event.body;
    
    // Validate the URL
    if (!text || !text.includes('sam.gov')) {
      return {
        status: 200,
        body: {
          response_type: "ephemeral",
          text: "❌ Please provide a valid SAM.gov URL\nUsage: `/import-rfp https://sam.gov/opp/[noticeId]/view`"
        }
      };
    }
    
    // Extract notice ID from URL
    const noticeIdMatch = text.match(/sam\.gov\/(?:opp|workspace\/contract\/opp)\/([a-zA-Z0-9]+)/);
    if (!noticeIdMatch) {
      return {
        status: 200,
        body: {
          response_type: "ephemeral",
          text: "❌ Could not extract Notice ID from URL\nExample: `https://sam.gov/opp/abc123def/view`"
        }
      };
    }
    
    const noticeId = noticeIdMatch[1];
    
    // Send immediate acknowledgment to Slack
    await $.send.http({
      method: "POST",
      url: response_url,
      data: {
        response_type: "in_channel",
        text: `🔄 Processing import for Notice ID: ${noticeId}...`,
        attachments: [{
          color: "warning",
          fields: [
            { title: "Requested by", value: user_name, short: true },
            { title: "Channel", value: channel_name, short: true },
            { title: "URL", value: text, short: false }
          ],
          footer: "RFP Import System",
          ts: Math.floor(Date.now() / 1000)
        }]
      }
    });
    
    // Trigger GitHub Actions to run the actual import
    // You'll need to set up a GitHub Personal Access Token
    const GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"; // Replace this!
    
    try {
      await $.send.http({
        method: "POST",
        url: "https://api.github.com/repos/finnegannorris/Crumb_finder/dispatches",
        headers: {
          "Authorization": `token ${GITHUB_TOKEN}`,
          "Accept": "application/vnd.github.v3+json"
        },
        data: {
          event_type: "slack-import",
          client_payload: {
            url: text,
            user: user_name,
            response_url: response_url,
            notice_id: noticeId
          }
        }
      });
      
      // Send the import details to the rfp-adder webhook
      const rfpAdderWebhook = "https://hooks.slack.com/services/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";
      
      await $.send.http({
        method: "POST",
        url: rfpAdderWebhook,
        data: {
          text: `📥 *Import Request Received*\n` +
                `Notice ID: ${noticeId}\n` +
                `Requested by: ${user_name}\n` +
                `Processing via GitHub Actions...`
        }
      });
      
    } catch (error) {
      // If GitHub trigger fails, notify via response URL
      await $.send.http({
        method: "POST",
        url: response_url,
        data: {
          response_type: "ephemeral",
          text: `❌ Failed to trigger import: ${error.message}\nYou can run manually: \`python scripts/import_rfp.py ${text}\``
        }
      });
    }
    
    // Return success to Slack
    return {
      status: 200,
      body: {
        response_type: "ephemeral",
        text: "✅ Import request submitted successfully"
      }
    };
  }
});