# GitHub Secrets Setup for Slack Integration

## ✅ Your Webhooks Are Working!

Both Slack channels should have received test messages. Now we need to add these to GitHub so the automated workflows can use them.

## Add to GitHub Secrets (Required for Automation)

### Quick Links
Go to: https://github.com/finnegannorris/Crumb_finder/settings/secrets/actions

### Secrets to Add:

1. **SLACK_WEBHOOK_URL** (Main channel for imports/daily)
   ```
   https://hooks.slack.com/services/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
   ```

2. **SLACK_OBITUARY_WEBHOOK_URL** (Obituary channel)
   ```
   https://hooks.slack.com/services/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
   ```

### Step-by-Step:

1. Go to your repository settings
2. Click "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add first secret:
   - Name: `SLACK_WEBHOOK_URL`
   - Secret: (paste the first webhook URL)
   - Click "Add secret"
5. Add second secret:
   - Name: `SLACK_OBITUARY_WEBHOOK_URL`  
   - Secret: (paste the second webhook URL)
   - Click "Add secret"

## What Each Channel Will Receive:

### Main Channel (First Webhook)
- ✅ Import notifications when using `/import-rfp`
- ✅ Daily RFP discovery summaries (8am ET)
- ✅ Error notifications
- ✅ System status updates

### Obituary Channel (Second Webhook)
- ⚰️ Weekly RFP obituaries (Fridays 5pm ET)
- 🪦 Expired opportunity memorials
- ⚠️ Death Watch alerts for soon-to-expire RFPs
- 💰 Estimated money left on the table

## Testing the Full System

### Test Import (Main Channel):
```bash
python test_import.py https://sam.gov/opp/[any-notice-id]/view
```

### Test Obituary (Obituary Channel):
```bash
python rfp_obituary.py --test --days 30
```

### Test via GitHub Actions:
1. Go to Actions tab in GitHub
2. Select "Weekly RFP Obituary"
3. Click "Run workflow"
4. Enable test mode
5. Check the obituary channel

## Verification Checklist:

- [x] Both webhooks tested locally
- [x] .env file updated with both webhooks
- [ ] GitHub secrets added (you need to do this)
- [ ] Test GitHub Action run

## Your Current Setup:

| Feature | Channel | Webhook | Status |
|---------|---------|---------|--------|
| Import notifications | Main | Configured | ✅ Ready |
| Daily discoveries | Main | Configured | ✅ Ready |
| Weekly obituaries | Obituary | Configured | ✅ Ready |
| Error alerts | Main | Configured | ✅ Ready |

Once you add the GitHub secrets, everything will be fully automated!