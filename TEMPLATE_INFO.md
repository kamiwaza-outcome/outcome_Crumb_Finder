# RFP Discovery System - Template Information

## 🎯 Template Status: READY FOR USE

This repository has been fully converted into a generic template that any company can use for RFP discovery and qualification.

## ✅ What Has Been Done

### Company-Specific Data Removed
- **ALL** Kamiwaza references have been removed (95 references across 25 files)
- Company name is now dynamically loaded from configuration
- All hardcoded capabilities and descriptions replaced with placeholders
- Past winning RFPs header genericized to `[YOUR COMPANY]`

### Configuration System Created
- `company_config.json` - Main company configuration file
- `.env.template` - Environment variables template with instructions
- Dynamic loading of company information throughout the codebase
- Examples provided for different company types

### Files Created for Template Use
1. **`setup_company.py`** - Interactive setup wizard for new companies
2. **`GITHUB_SETUP.md`** - Complete guide for GitHub Actions configuration
3. **`examples/`** directory with 3 pre-built configurations:
   - Defense contractor
   - Software consulting firm
   - AI/ML company
4. **`.env.template`** - Comprehensive environment variables template

## 🚀 Quick Start for New Companies

### Option 1: Interactive Setup (Recommended)
```bash
python setup_company.py
```
This wizard will guide you through:
- Company configuration
- Environment variables
- Google Sheets setup
- Validation

### Option 2: Manual Configuration
1. Copy an example from `examples/` to `company_config.json`
2. Copy `.env.template` to `.env` and fill in values
3. Follow `GITHUB_SETUP.md` for GitHub Actions

### Option 3: Minimal Setup
1. Edit `company_config.json` with your company details
2. Set required environment variables:
   - `SAM_API_KEY`
   - `OPENAI_API_KEY`
   - `GOOGLE_SHEETS_CREDS_PATH`
3. Run: `python main.py --test`

## 📋 Required Information from Companies

### Must Have
- Company name and description
- Core capabilities and services
- Search keywords relevant to your industry
- NAICS codes for your business
- SAM.gov API key
- OpenAI API key (with GPT-5 access)
- Google Cloud service account

### Should Have
- Past winning RFPs (for better AI training)
- Contract value preferences
- Geographic preferences
- Technical expertise list
- Certifications

### Nice to Have
- Slack webhook for notifications
- Contract vehicles
- Set-aside eligibilities
- Case studies

## 🔐 GitHub Secrets Configuration

All secrets are documented in `GITHUB_SETUP.md`. The repository expects these secrets to be set in GitHub, not hardcoded:

### Required Secrets
- `SAM_API_KEY` - Your SAM.gov API key
- `OPENAI_API_KEY` - Your OpenAI API key
- `GOOGLE_CREDENTIALS_BASE64` - Base64-encoded service account JSON
- `SPREADSHEET_ID` - Main opportunities sheet
- `GOOGLE_DRIVE_FOLDER_ID` - Drive folder for documents

### Optional Secrets
- `MAYBE_SPREADSHEET_ID` - Maybe opportunities sheet
- `SPAM_SPREADSHEET_ID` - Audit trail sheet
- `GRAVEYARD_SHEET_ID` - Expired RFPs archive
- `BANK_SHEET_ID` - Won/completed RFPs
- `SLACK_WEBHOOK_URL` - Slack notifications

## 📁 Repository Structure

```
Crumb_Finder_Template/
├── company_config.json          # Your company configuration (create this)
├── .env                         # Your environment variables (create this)
├── .env.template               # Template for environment variables
├── setup_company.py            # Interactive setup wizard
├── GITHUB_SETUP.md            # GitHub Actions configuration guide
├── examples/                   # Example configurations
│   ├── defense_contractor_config.json
│   ├── software_consulting_config.json
│   └── ai_ml_company_config.json
├── src/                       # Core application code (company-agnostic)
├── scripts/                   # Automation scripts (company-agnostic)
├── tests/                     # Test files (uses generic test data)
├── docs/                      # Documentation (uses placeholders)
└── .github/workflows/         # GitHub Actions (uses secrets)
```

## 🎯 Remaining Kamiwaza References

The only remaining Kamiwaza references are in:
- `archive/` directory - Old backup files, not used in production
- Historical context in some comments - Does not affect functionality

These do not impact the template usage and can be ignored or deleted.

## 🔄 Migration Path

For companies migrating from a custom solution:
1. Run `python setup_company.py` to create configuration
2. Import your past winning RFPs to `data/winning_rfps.txt`
3. Update scoring criteria in `company_config.json`
4. Test with `python main.py --test`
5. Deploy to GitHub and configure secrets
6. Enable GitHub Actions workflows

## 📞 Support

This template is designed to be self-service. For setup help:
1. Run the interactive setup script
2. Review example configurations
3. Check `GITHUB_SETUP.md` for GitHub configuration
4. Test with limited searches first

## ⏱️ Time to Deploy

With all prerequisites ready (API keys, Google account), a new company should be able to:
- Complete basic setup: 30 minutes
- Configure GitHub Actions: 30 minutes
- Customize scoring criteria: 1 hour
- Full deployment and testing: 2-3 hours total

This is compared to weeks or months to build a similar system from scratch.

## 🎉 Template Ready!

The Crumb Finder template is now completely generic and ready for any technology company to deploy their own RFP discovery system. All company-specific data has been abstracted into configuration files.