# 🛠️ Crumb Finder - Complete Setup Guide

This comprehensive guide will walk you through setting up the Crumb Finder Enterprise RFP Intelligence Platform for your company. This system is a template that requires configuration for your specific organization.

## 📋 Prerequisites

Before beginning setup, ensure you have:
- SAM.gov account with API access
- OpenAI account with GPT-5 API access
- Google Cloud account
- GitHub account (for automation)
- Slack workspace (optional)

## 🚀 Quick Start Setup

### Step 1: Clone and Prepare Repository
```bash
git clone https://github.com/[your-username]/Crumb_Finder_Template.git
cd Crumb_Finder_Template
pip install -r requirements.txt
```

### Step 2: Configure Your Company Profile

#### Option A: Interactive Setup (Recommended)
```bash
python setup_company.py
```
This wizard will guide you through creating:
- Company configuration file
- Environment variables
- Google Sheets setup

#### Option B: Manual Configuration
1. **Create company configuration** (`company_config.json`):
```bash
# Copy an example template
cp examples/software_consulting_config.json company_config.json
# Edit with your company details
```

2. **Key fields to customize**:
```json
{
  "company": {
    "name": "Your Company Name",
    "profile": "2-3 sentences about your company and capabilities",
    "capabilities": ["Your core services", "Key technologies", "Domain expertise"]
  },
  "rfp_targeting": {
    "keywords": ["Keywords relevant to your business"],
    "naics_codes": ["Your NAICS codes"]
  },
  "scoring_criteria": {
    "minimum_contract_value": 100000,
    "maximum_contract_value": 10000000
  }
}
```

### Step 3: Obtain Required API Keys

#### SAM.gov API Key
1. Register at [SAM.gov](https://sam.gov)
2. Navigate to [Federal Service Desk](https://fsd.gov)
3. Sign in and request "System Account"
4. Request API key

#### OpenAI API Key
1. Sign up at [OpenAI Platform](https://platform.openai.com)
2. Navigate to API keys section
3. Create new secret key
4. Ensure you have GPT-5 API access

### Step 4: Google Cloud Setup

#### Create Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable these APIs:
   - Google Sheets API
   - Google Drive API
   - Google Docs API (optional)
4. Create service account:
   ```
   IAM & Admin → Service Accounts → Create Service Account
   Name: rfp-discovery-bot
   Role: Editor (or custom role with Sheets/Drive permissions)
   ```
5. Generate JSON key:
   - Click on service account
   - Keys tab → Add Key → Create New Key → JSON
   - Save the downloaded file securely

#### Create Google Sheets
Create 4 sheets manually or let the system auto-create:
1. **Main Sheet** - Qualified opportunities (7+ score)
2. **Maybe Sheet** - Borderline opportunities (4-6 score)
3. **Spam Sheet** - All evaluated RFPs (audit trail)
4. **Graveyard Sheet** - Expired RFPs (optional)

Share each sheet with your service account email (found in JSON key file).

#### Create Google Drive Folder
1. Create a folder in Google Drive for RFP documents
2. Share with service account email
3. Copy folder ID from URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`

### Step 5: Environment Configuration

Create `.env` file from template:
```bash
cp .env.template .env
```

Edit `.env` with your values:
```bash
# Required API Keys
SAM_API_KEY=your_sam_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Google Service Account (path to JSON file)
GOOGLE_SHEETS_CREDS_PATH=/path/to/service-account-key.json

# Google Sheets IDs (leave empty to auto-create)
SPREADSHEET_ID=
MAYBE_SPREADSHEET_ID=
SPAM_SPREADSHEET_ID=

# Google Drive Folder
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here

# Company Configuration
COMPANY_CONFIG_PATH=./company_config.json

# Optional: Slack Integration
SLACK_WEBHOOK_URL=
```

### Step 6: Customize Past Performance (Optional but Recommended)

Add your company's past winning RFPs to improve AI accuracy:

1. Edit `data/winning_rfps.txt`
2. Replace example RFPs with your actual wins
3. Follow the format:
```
Project-ID: Project Title
-----------------------------------
Description of the work performed and technologies used.
```

### Step 7: Test Your Configuration

```bash
# Test with limited RFPs
python main.py --test

# If successful, run full discovery
python main.py --run-now
```

### Step 8: GitHub Actions Setup (For Automation)

1. **Fork or push to your GitHub repository**

2. **Add GitHub Secrets** (Settings → Secrets and variables → Actions):

   Required secrets:
   - `SAM_API_KEY` - Your SAM.gov API key
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `GOOGLE_CREDENTIALS_BASE64` - Base64 encoded service account JSON
   - `SPREADSHEET_ID` - Main sheet ID
   - `GOOGLE_DRIVE_FOLDER_ID` - Drive folder ID

   To encode Google credentials:
   ```bash
   # macOS/Linux:
   base64 -i service-account-key.json | pbcopy

   # Windows PowerShell:
   [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("service-account-key.json")) | Set-Clipboard
   ```

3. **Enable GitHub Actions**:
   - Go to Actions tab
   - Enable workflows
   - Test with manual trigger

### Step 9: Verify Everything Works

1. **Check Google Sheets**: Verify sheets are being populated
2. **Check Google Drive**: Confirm RFP folders are created
3. **Review AI Scores**: Ensure scoring aligns with your criteria
4. **Test Slack**: Confirm notifications arrive (if configured)

### Step 10: Production Deployment

Once testing is successful:
1. GitHub Actions will run automatically at 5 AM ET daily
2. Monitor the Actions tab for any failures
3. Review qualified RFPs in your main Google Sheet
4. Adjust `company_config.json` scoring criteria as needed

## 📋 Configuration Checklist

- [ ] Company configuration file created
- [ ] SAM.gov API key obtained
- [ ] OpenAI API key with GPT-5 access
- [ ] Google service account created
- [ ] Google Sheets created and shared
- [ ] Google Drive folder created and shared
- [ ] Environment variables configured
- [ ] Past performance data added
- [ ] Local testing successful
- [ ] GitHub secrets configured
- [ ] GitHub Actions enabled
- [ ] First automated run successful

## 🚨 Troubleshooting Common Setup Issues

### Issue: "Authentication failed" for Google Sheets
**Solution**:
- Verify service account JSON file path is correct
- Ensure sheets are shared with service account email
- Check that Sheets API is enabled in Google Cloud Console

### Issue: "SAM.gov API rate limit exceeded"
**Solution**:
- Reduce concurrent searches in test mode
- Check your API key limits on SAM.gov
- Use smaller date ranges initially

### Issue: "OpenAI API error: insufficient_quota"
**Solution**:
- Add credits to your OpenAI account
- Verify GPT-5 access is enabled
- Start with test mode (fewer RFPs)

### Issue: "No RFPs being qualified"
**Solution**:
- Review your `company_config.json` keywords
- Check if scoring thresholds are too high
- Ensure company profile accurately reflects capabilities
- Add more relevant past winning RFPs

### Issue: GitHub Actions failing
**Solution**:
- Verify all secrets are set correctly
- Check workflow logs for specific errors
- Test locally first with same credentials
- Ensure base64 encoding of Google credentials is correct

## 📊 Configuration Options

### Processing Modes
| Mode | Description | Use Case |
|------|-------------|----------|
| **OVERKILL** | No filters, ALL RFPs | Complete market coverage |
| **Normal** | NAICS + keyword filters | Targeted discovery |
| **Test** | Limited to 20 RFPs | Development/testing |

### Concurrent Processing Limits
```python
# config.py settings with new token limits
MAX_CONCURRENT_DEEP = 130    # GPT-5 deep analysis threads
MAX_CONCURRENT_MINI = 400    # GPT-5-mini screening threads
GPT5_MAX_TOKENS = 100000      # Deep analysis token limit
GPT5_MINI_MAX_TOKENS = 32000  # Screening token limit
MIN_REQUEST_INTERVAL = 0.002  # 2ms between requests
```

### Search Configuration
```python
# NAICS Codes (IT/AI Services)
NAICS_CODES = [
    '541511',  # Custom Computer Programming
    '541512',  # Computer Systems Design
    '541519',  # Other Computer Related
    '518210',  # Data Processing & Hosting
    '541690'   # Scientific & Technical Consulting
]

# AI/ML Keywords (25+ terms)
AI_KEYWORDS = [
    'artificial intelligence', 'machine learning',
    'deep learning', 'neural network', 'NLP',
    'computer vision', 'predictive analytics',
    'data science', 'automation', 'chatbot',
    # ... and more
]
```

## 🔧 Advanced Features

### Deduplication System
- **Multi-strategy matching**: Notice ID, solicitation number, fuzzy title
- **Cross-sheet detection**: Prevents duplicates across all sheets
- **Performance caching**: 30-minute TTL for speed
- **Fuzzy matching**: Catches near-duplicates

### Weekend Intelligence
- **Automatic detection**: Identifies Monday runs
- **Multi-day search**: Covers Friday-Sunday postings
- **Volume adaptation**: Adjusts processing for accumulated RFPs
- **Never miss opportunities**: Complete weekend coverage

### Carryover Management
- **High-volume handling**: Queue system for busy days
- **Prioritization**: Important RFPs processed first
- **Automatic resumption**: Continues where left off
- **Progress tracking**: Monitor carryover status

### Error Recovery
- **Circuit breakers**: Prevent cascade failures
- **Exponential backoff**: Smart retry logic
- **Partial saves**: Preserve successful results
- **Automatic recovery**: Self-healing capabilities

## 🚦 Monitoring & Alerts

### Slack Notifications
- **Daily Summaries**: Processing metrics and discoveries
- **High-Value Alerts**: Immediate notification for 8+ scores
- **Weekly Obituaries**: Friday 5PM ET memorial service
- **Error Notifications**: System failures and warnings

### Health Monitoring
- **API Status**: Track all external service health
- **Processing Metrics**: Volume, speed, success rates
- **Error Tracking**: Detailed logging and recovery
- **Performance Analytics**: TPM usage and optimization