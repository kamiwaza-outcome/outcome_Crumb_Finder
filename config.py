import os
import json
from datetime import datetime, timezone
from typing import Dict, Any

class Config:
    # Load company configuration
    COMPANY_CONFIG_PATH = os.getenv('COMPANY_CONFIG_PATH', './company_config.json')

    # Initialize company configuration
    _company_config = None

    @classmethod
    def load_company_config(cls):
        """Load company configuration from JSON file"""
        try:
            if os.path.exists(cls.COMPANY_CONFIG_PATH):
                with open(cls.COMPANY_CONFIG_PATH, 'r') as f:
                    return json.load(f)
            else:
                # Return default structure if config doesn't exist
                return {
                    'company': {'name': 'YOUR_COMPANY', 'profile': 'Company profile not configured'},
                    'rfp_targeting': {
                        'keywords': ['software', 'technology', 'consulting'],
                        'naics_codes': ['541511', '541512', '541519']
                    }
                }
        except Exception as e:
            print(f"Warning: Could not load company config: {e}")
            return {
                'company': {'name': 'YOUR_COMPANY', 'profile': 'Company profile not configured'},
                'rfp_targeting': {'keywords': [], 'naics_codes': []}
            }

    @classmethod
    def get_company_config(cls):
        """Get cached company configuration"""
        if cls._company_config is None:
            cls._company_config = cls.load_company_config()
        return cls._company_config

    # API Keys (will be set via environment variables or direct assignment)
    SAM_API_KEY = os.getenv('SAM_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    GOOGLE_SHEETS_CREDS_PATH = os.getenv('GOOGLE_SHEETS_CREDS_PATH', '/Users/finnegannorris/Downloads/rfp-discovery-system-e67dc59c8ee1.json')
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')  # Main channel for imports/daily updates
    SLACK_OBITUARY_WEBHOOK_URL = os.getenv('SLACK_OBITUARY_WEBHOOK_URL', '')  # Separate channel for obituaries
    
    # Google Drive Configuration
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    DAILY_RFPS_FOLDER_ID = os.getenv('DAILY_RFPS_FOLDER_ID', '1n9XWAHZL9QiDQ5FPdYfzDCceZaVx7Mrq')  # Subfolder for daily RFP documents
    
    # Google Sheets Configuration
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '')
    MAYBE_SPREADSHEET_ID = os.getenv('MAYBE_SPREADSHEET_ID', '')
    REJECTED_SPREADSHEET_ID = os.getenv('REJECTED_SPREADSHEET_ID', '')
    SPAM_SPREADSHEET_ID = os.getenv('SPAM_SPREADSHEET_ID', '')
    GRAVEYARD_SPREADSHEET_ID = os.getenv('GRAVEYARD_SPREADSHEET_ID', '1Wmyl1dAslRASfuF8WcuOgb4tEo3HlZglm2DnEo-0MhQ')  # Archive for expired RFPs
    BANK_SPREADSHEET_ID = os.getenv('BANK_SPREADSHEET_ID', '1xG9R1nzLrMYbx57gtzlIHuA2glidZw3I6X_pSObrXhM')  # Archive for completed RFPs
    SHEET_NAME = os.getenv('SHEET_NAME', 'RFP Opportunities')
    
    # SAM.gov API Configuration
    SAM_BASE_URL = 'https://api.sam.gov/opportunities/v2/search'
    SAM_API_TIMEOUT = 30  # 30 second timeout for SAM API calls
    
    # OpenAI Configuration
    GPT_MODEL = 'gpt-5'  # Using GPT-5 as specified
    
    # Search Keywords - loaded from company config
    @classmethod
    def get_search_keywords(cls):
        """Get search keywords from company configuration"""
        config = cls.get_company_config()
        return config.get('rfp_targeting', {}).get('keywords', [
            'software', 'technology', 'consulting', 'development',
            'integration', 'implementation', 'support', 'services'
        ])
    
    # NAICS codes - loaded from company config
    @classmethod
    def get_naics_codes(cls):
        """Get NAICS codes from company configuration"""
        config = cls.get_company_config()
        return config.get('rfp_targeting', {}).get('naics_codes', [
            '541511',  # Custom Computer Programming Services
            '541512',  # Computer Systems Design Services
            '541519',  # Other Computer Related Services
        ])
    
    # Schedule Configuration
    RUN_TIME = "17:00"  # 5:00 PM Eastern
    TIMEZONE = "America/New_York"
    
    # NEW: Massive TPM Limits (2M for GPT-5, 4M for mini!)
    MAX_CONCURRENT_DEEP = 130    # Was 30, now 130 with 2M TPM
    MAX_CONCURRENT_MINI = 400    # Was 200, now 400 with 4M TPM
    GPT5_MAX_TOKENS = 100000     # Was 50k, now 100k for deeper analysis
    GPT5_MINI_MAX_TOKENS = 32000 # Was 16k, now 32k for better screening
    MIN_REQUEST_INTERVAL = 0.002 # 2ms between requests (faster with higher limits)
    
    # Processing Limits
    MAX_DAILY_RFPS = 20000       # Massive capacity with new token limits!
    OPENAI_TIMEOUT = 300         # 5 minute timeout for complex analysis
    MAX_RETRIES = 5              # Max retries for API calls
    CIRCUIT_BREAKER_THRESHOLD = 3  # Failures before circuit opens
    CIRCUIT_BREAKER_TIMEOUT = 60   # Seconds before retry after circuit opens
    
    # Company Information - loaded from company config
    @classmethod
    def get_company_info(cls):
        """Get company profile information"""
        config = cls.get_company_config()
        company = config.get('company', {})
        return company.get('profile', 'Company profile not configured. Please update company_config.json')

    @classmethod
    def get_company_name(cls):
        """Get company name"""
        config = cls.get_company_config()
        company = config.get('company', {})
        return company.get('name', 'YOUR_COMPANY')

    @classmethod
    def get_company_capabilities(cls):
        """Get company capabilities list"""
        config = cls.get_company_config()
        company = config.get('company', {})
        return company.get('capabilities', [
            'Software development and consulting',
            'Technology integration and implementation',
            'Data analysis and processing',
            'Business process automation',
            'Legacy system modernization',
            'Cloud solutions and deployment'
        ])

    # Legacy support - will be removed
    COMPANY_INFO = property(lambda self: Config.get_company_info())
    
    
    @classmethod
    def get_search_params(cls) -> Dict[str, Any]:
        """Get default search parameters for SAM API"""
        return {
            'api_key': cls.SAM_API_KEY,
            'postedFrom': datetime.now(timezone.utc).strftime('%m/%d/%Y'),
            'postedTo': datetime.now(timezone.utc).strftime('%m/%d/%Y'),
            'limit': 100,
            'offset': 0,
            'active': 'true'
        }