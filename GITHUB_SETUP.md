# GitHub Actions Setup Guide

This guide explains how to configure GitHub Actions for automated RFP discovery.

## Required GitHub Secrets

The following secrets must be configured in your GitHub repository for the workflows to function properly.

**Navigate to: Settings → Secrets and variables → Actions → New repository secret**

### 🔑 API Keys

| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `SAM_API_KEY` | SAM.gov API key for searching RFPs | Register at [SAM.gov](https://sam.gov/apis) |
| `OPENAI_API_KEY` | OpenAI API key for GPT-5 access | Get from [OpenAI Platform](https://platform.openai.com/api-keys) |

### 📊 Google Sheets Configuration

| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `GOOGLE_CREDENTIALS_BASE64` | Base64-encoded service account JSON | See [Google Setup](#google-service-account-setup) below |
| `SPREADSHEET_ID` | Main qualified opportunities sheet ID | Create manually or let system auto-create |
| `MAYBE_SPREADSHEET_ID` | Maybe/borderline opportunities sheet ID | Create manually or let system auto-create |
| `SPAM_SPREADSHEET_ID` | Low-relevance opportunities sheet ID | Create manually or let system auto-create |
| `GRAVEYARD_SHEET_ID` | Archive for expired RFPs | Optional - for weekly obituaries |
| `BANK_SHEET_ID` | Archive for completed/won RFPs | Optional - for completed projects |

### 📁 Google Drive Configuration

| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `GOOGLE_DRIVE_FOLDER_ID` | Folder ID for storing RFP documents | Create folder in Drive, extract ID from URL |

### 💬 Slack Integration (Optional)

| Secret Name | Description | How to Obtain |
|------------|-------------|---------------|
| `SLACK_WEBHOOK_URL` | Webhook for notifications | Create at [Slack API](https://api.slack.com/messaging/webhooks) |
| `SLACK_OBITUARY_WEBHOOK_URL` | Separate webhook for obituaries | Optional - for weekly memorial notifications |

## Google Service Account Setup

### Step 1: Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Note the Project ID

### Step 2: Enable Required APIs
Enable the following APIs in your project:
- Google Sheets API
- Google Drive API
- Google Docs API (optional, for document creation)

### Step 3: Create Service Account
1. Navigate to **IAM & Admin → Service Accounts**
2. Click **Create Service Account**
3. Name it (e.g., "rfp-discovery-bot")
4. Grant role: **Editor** or create custom role
5. Click **Done**

### Step 4: Generate JSON Key
1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key → Create New Key**
4. Choose **JSON** format
5. Save the downloaded file

### Step 5: Convert to Base64
```bash
# On macOS/Linux:
base64 -i service-account-key.json | pbcopy

# On Windows (PowerShell):
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("service-account-key.json")) | Set-Clipboard
```

### Step 6: Add to GitHub Secrets
1. Go to repository **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `GOOGLE_CREDENTIALS_BASE64`
4. Value: Paste the base64 string
5. Click **Add secret**

### Step 7: Share Sheets with Service Account
1. Find service account email in JSON file (e.g., `rfp-bot@project.iam.gserviceaccount.com`)
2. Share each Google Sheet with this email as **Editor**
3. Share the Drive folder with this email as **Editor**

## Workflow Configurations

### Daily RFP Discovery (`daily-rfp-discovery.yml`)
- **Schedule**: 5:00 AM ET Tuesday-Saturday
- **Modes**:
  - `overkill`: Process ALL RFPs (2000+) - Default
  - `normal`: Standard filters (200-500 RFPs)
  - `test`: Test mode (20 RFPs)
- **Manual Trigger**: Can be run manually with custom parameters

### Weekly RFP Obituary (`weekly-rfp-obituary.yml`)
- **Schedule**: Mondays at 9:00 AM ET
- **Purpose**: Archive expired RFPs with humorous memorials
- **Requirements**: `GRAVEYARD_SHEET_ID` must be set

### Import RFP (`import-rfp.yml`)
- **Trigger**: Manual only
- **Purpose**: Import specific RFP by URL or notice ID
- **Use Case**: When you find an RFP outside the system

## Testing Your Setup

### 1. Verify Secrets
Run the manual workflow with test mode:
1. Go to **Actions** tab
2. Select **Daily RFP Discovery**
3. Click **Run workflow**
4. Select **test** mode
5. Click **Run workflow**

### 2. Check Logs
- Click on the workflow run
- Expand each step to see detailed logs
- Look for any authentication errors

### 3. Common Issues

| Issue | Solution |
|-------|----------|
| "Authentication failed" | Check `GOOGLE_CREDENTIALS_BASE64` is properly encoded |
| "Sheet not found" | Verify sheet IDs and sharing permissions |
| "API rate limit" | Ensure OpenAI API has sufficient credits |
| "SAM.gov error" | Verify API key and check SAM.gov status |

## Security Best Practices

1. **Never commit secrets to code**
2. **Rotate API keys regularly**
3. **Use minimal permissions for service accounts**
4. **Monitor usage and costs**
5. **Set up billing alerts for APIs**

## Environment Variables Reference

These can be set as repository secrets or workflow environment variables:

```yaml
# Required
SAM_API_KEY: Your SAM.gov API key
OPENAI_API_KEY: Your OpenAI API key
GOOGLE_CREDENTIALS_BASE64: Base64-encoded service account JSON
SPREADSHEET_ID: Main opportunities sheet ID

# Recommended
MAYBE_SPREADSHEET_ID: Maybe opportunities sheet ID
SPAM_SPREADSHEET_ID: Spam/audit sheet ID
GOOGLE_DRIVE_FOLDER_ID: Drive folder for documents

# Optional
GRAVEYARD_SHEET_ID: Archive for expired RFPs
BANK_SHEET_ID: Archive for won/completed RFPs
SLACK_WEBHOOK_URL: Slack notifications webhook
SLACK_OBITUARY_WEBHOOK_URL: Obituary notifications webhook
COMPANY_CONFIG_PATH: Path to company configuration (defaults to ./company_config.json)
```

## Support

If you encounter issues:
1. Check the workflow logs in the Actions tab
2. Verify all secrets are properly set
3. Ensure service account has correct permissions
4. Test with the manual trigger in test mode first

For the system to work properly, all required secrets must be configured. Optional secrets enhance functionality but are not required for basic operation.