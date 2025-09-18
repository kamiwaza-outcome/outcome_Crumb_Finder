#!/usr/bin/env python3
"""
RFP Discovery System - Company Setup Script

This script helps new companies configure the RFP Discovery System for their organization.
It will guide you through setting up:
1. Company configuration (name, profile, capabilities)
2. Google Sheets creation and configuration
3. Google Drive folder setup
4. Environment variables
5. Initial validation
"""

import os
import json
import sys
from pathlib import Path
import subprocess

def print_header():
    """Display welcome header"""
    print("\n" + "="*70)
    print("  RFP DISCOVERY SYSTEM - COMPANY SETUP")
    print("="*70 + "\n")

def get_input(prompt, default=None, required=True):
    """Get user input with optional default value"""
    display_prompt = f"{prompt}"
    if default:
        display_prompt += f" [{default}]"
    display_prompt += ": "

    value = input(display_prompt).strip()

    if not value and default:
        return default

    if required and not value:
        print("  ⚠️  This field is required.")
        return get_input(prompt, default, required)

    return value

def get_multi_line_input(prompt):
    """Get multi-line input from user"""
    print(f"{prompt} (Enter 'END' on a new line when done):")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == 'END':
            break
        lines.append(line)
    return '\n'.join(lines)

def get_list_input(prompt):
    """Get list input from user"""
    print(f"{prompt} (Enter one per line, 'END' when done):")
    items = []
    while True:
        item = input().strip()
        if item.upper() == 'END':
            break
        if item:
            items.append(item)
    return items

def create_company_config():
    """Create company configuration file"""
    print("\n📋 COMPANY CONFIGURATION")
    print("-" * 40)

    config = {
        "company": {},
        "capabilities": {},
        "rfp_targeting": {},
        "scoring_criteria": {},
        "past_performance": {},
        "ai_evaluation_prompts": {}
    }

    # Basic company information
    print("\n1. Basic Company Information:")
    config["company"]["name"] = get_input("Company name")
    config["company"]["website"] = get_input("Company website", "https://example.com", False)
    config["company"]["industry"] = get_input("Primary industry (e.g., Technology, Defense, Consulting)")

    print("\n2. Company Profile (2-3 sentences about your company):")
    config["company"]["profile"] = get_multi_line_input("Company profile")

    # Capabilities
    print("\n3. Core Capabilities:")
    config["capabilities"]["core_capabilities"] = get_list_input("Enter core capabilities")

    print("\n4. Technical Expertise (languages, platforms, tools):")
    config["capabilities"]["technical_expertise"] = get_list_input("Enter technical expertise")

    print("\n5. Certifications (optional):")
    config["capabilities"]["certifications"] = get_list_input("Enter certifications")

    # RFP Targeting
    print("\n6. RFP Search Keywords:")
    print("   (Keywords to search for in RFP titles/descriptions)")
    config["rfp_targeting"]["keywords"] = get_list_input("Enter keywords")

    print("\n7. NAICS Codes (press Enter to use defaults):")
    naics_input = get_input("Enter NAICS codes (comma-separated)", "", False)
    if naics_input:
        config["rfp_targeting"]["naics_codes"] = [code.strip() for code in naics_input.split(',')]
    else:
        config["rfp_targeting"]["naics_codes"] = [
            "541511",  # Custom Computer Programming Services
            "541512",  # Computer Systems Design Services
            "541519"   # Other Computer Related Services
        ]

    # Scoring criteria
    print("\n8. Contract Value Preferences:")
    min_val = get_input("Minimum contract value (USD)", "100000", False)
    max_val = get_input("Maximum contract value (USD)", "10000000", False)
    config["scoring_criteria"]["minimum_contract_value"] = int(min_val) if min_val else 100000
    config["scoring_criteria"]["maximum_contract_value"] = int(max_val) if max_val else 10000000

    # AI evaluation prompts
    print("\n9. AI Evaluation Guidance:")
    config["ai_evaluation_prompts"]["company_strengths"] = get_input(
        "What are your company's unique strengths? (1-2 sentences)"
    )
    config["ai_evaluation_prompts"]["ideal_opportunity"] = get_input(
        "Describe your ideal RFP opportunity (1-2 sentences)"
    )

    # Add capabilities list to company object for easier access
    config["company"]["capabilities"] = config["capabilities"]["core_capabilities"]

    return config

def save_config(config, filename="company_config.json"):
    """Save configuration to JSON file"""
    with open(filename, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"\n✅ Configuration saved to {filename}")

def create_env_file():
    """Create .env file from template"""
    print("\n🔐 ENVIRONMENT VARIABLES SETUP")
    print("-" * 40)

    env_content = []

    # Check if .env.template exists
    if not Path('.env.template').exists():
        print("  ⚠️  .env.template not found. Creating basic .env file...")
        env_content = [
            "# API Keys",
            f"SAM_API_KEY={get_input('SAM.gov API Key')}",
            f"OPENAI_API_KEY={get_input('OpenAI API Key')}",
            "",
            "# Google Configuration",
            f"GOOGLE_SHEETS_CREDS_PATH={get_input('Path to Google service account JSON')}",
            f"GOOGLE_DRIVE_FOLDER_ID={get_input('Google Drive folder ID', '', False)}",
            "",
            "# Slack (optional)",
            f"SLACK_WEBHOOK_URL={get_input('Slack webhook URL (optional)', '', False)}",
            "",
            "# Company Config",
            "COMPANY_CONFIG_PATH=./company_config.json"
        ]
    else:
        print("\nPlease provide the following API keys and configurations:")
        print("(Refer to .env.template for detailed instructions)\n")

        env_content.append("# Generated by setup_company.py")
        env_content.append("")
        env_content.append("# API Keys")
        env_content.append(f"SAM_API_KEY={get_input('SAM.gov API Key')}")
        env_content.append(f"OPENAI_API_KEY={get_input('OpenAI API Key')}")
        env_content.append("")
        env_content.append("# Google Configuration")
        env_content.append(f"GOOGLE_SHEETS_CREDS_PATH={get_input('Path to Google service account JSON')}")
        env_content.append(f"GOOGLE_DRIVE_FOLDER_ID={get_input('Google Drive folder ID (leave empty to create)', '', False)}")
        env_content.append("")
        env_content.append("# Google Sheets (leave empty to auto-create)")
        env_content.append(f"SPREADSHEET_ID={get_input('Main spreadsheet ID (leave empty to create)', '', False)}")
        env_content.append(f"MAYBE_SPREADSHEET_ID={get_input('Maybe spreadsheet ID (leave empty to create)', '', False)}")
        env_content.append(f"REJECTED_SPREADSHEET_ID={get_input('Rejected spreadsheet ID (leave empty to create)', '', False)}")
        env_content.append(f"SPAM_SPREADSHEET_ID={get_input('Spam spreadsheet ID (leave empty to create)', '', False)}")
        env_content.append("")
        env_content.append("# Slack Integration (optional)")
        env_content.append(f"SLACK_WEBHOOK_URL={get_input('Slack webhook URL (optional)', '', False)}")
        env_content.append("")
        env_content.append("# Company Configuration")
        env_content.append("COMPANY_CONFIG_PATH=./company_config.json")

    # Save .env file
    with open('.env', 'w') as f:
        f.write('\n'.join(env_content))

    print("\n✅ Environment variables saved to .env")
    print("  ⚠️  Remember: Never commit .env to version control!")

def create_google_sheets():
    """Guide user through Google Sheets setup"""
    print("\n📊 GOOGLE SHEETS SETUP")
    print("-" * 40)
    print("\nThe system requires 4 Google Sheets:")
    print("1. Main sheet - Qualified opportunities")
    print("2. Maybe sheet - Borderline opportunities")
    print("3. Rejected sheet - Audit trail")
    print("4. Spam sheet - Low-relevance opportunities")
    print("\nYou can either:")
    print("  A) Let the system create them automatically (recommended)")
    print("  B) Create them manually and provide the IDs")

    choice = get_input("\nChoice (A/B)", "A")

    if choice.upper() == 'A':
        print("\n✅ Sheets will be created automatically on first run.")
        print("   Make sure your service account has the necessary permissions.")
    else:
        print("\n📝 Please create 4 Google Sheets and add their IDs to the .env file")
        print("   Share each sheet with your service account email.")

def validate_setup():
    """Validate the setup configuration"""
    print("\n🔍 VALIDATING SETUP")
    print("-" * 40)

    issues = []

    # Check company config
    if not Path('company_config.json').exists():
        issues.append("❌ company_config.json not found")
    else:
        print("✅ Company configuration found")

    # Check .env
    if not Path('.env').exists():
        issues.append("❌ .env file not found")
    else:
        print("✅ Environment variables configured")

        # Check for required variables
        from dotenv import load_dotenv
        load_dotenv()

        required_vars = ['SAM_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_SHEETS_CREDS_PATH']
        for var in required_vars:
            if not os.getenv(var):
                issues.append(f"❌ {var} not set in .env")

    # Check dependencies
    try:
        import openai
        print("✅ OpenAI package installed")
    except ImportError:
        issues.append("❌ OpenAI package not installed (run: pip install -r requirements.txt)")

    if issues:
        print("\n⚠️  Setup Issues Found:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("\n🎉 Setup validation successful!")
        return True

def print_next_steps():
    """Display next steps for the user"""
    print("\n📋 NEXT STEPS")
    print("-" * 40)
    print("\n1. Ensure your Google service account has:")
    print("   - Google Sheets API enabled")
    print("   - Google Drive API enabled")
    print("   - Proper permissions to create/edit sheets and folders")
    print("\n2. Test the system with limited searches:")
    print("   python main.py --test")
    print("\n3. Run a full discovery:")
    print("   python main.py --run-now")
    print("\n4. Schedule daily runs (optional):")
    print("   python main.py --schedule")
    print("\n5. For GitHub Actions automation:")
    print("   - Add all .env variables as GitHub Secrets")
    print("   - Enable the workflow in .github/workflows/")

def main():
    """Main setup flow"""
    print_header()

    print("This wizard will help you configure the RFP Discovery System")
    print("for your company. Let's get started!\n")

    # Step 1: Create company configuration
    if get_input("Create company configuration? (y/n)", "y").lower() == 'y':
        config = create_company_config()
        save_config(config)

    # Step 2: Setup environment variables
    if get_input("\nSetup environment variables? (y/n)", "y").lower() == 'y':
        create_env_file()

    # Step 3: Google Sheets guidance
    if get_input("\nSetup Google Sheets? (y/n)", "y").lower() == 'y':
        create_google_sheets()

    # Step 4: Validate setup
    print("\n")
    if validate_setup():
        print_next_steps()
        print("\n✅ Setup complete! Your RFP Discovery System is ready to use.")
    else:
        print("\n⚠️  Please resolve the issues above before running the system.")

    print("\n" + "="*70)
    print("  Thank you for using RFP Discovery System!")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup error: {str(e)}")
        sys.exit(1)