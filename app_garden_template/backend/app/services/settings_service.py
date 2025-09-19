"""Settings service for managing RFP Discovery configuration"""

import json
import os
from pathlib import Path
from typing import Optional
import logging

from app.models.settings import Settings, APIKeys, CompanyProfile

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing application settings"""

    def __init__(self):
        """Initialize settings service"""
        self.settings_dir = Path("data/settings")
        self.settings_file = self.settings_dir / "settings.json"
        self.settings_dir.mkdir(parents=True, exist_ok=True)

        # Load settings on initialization
        self.settings = self.load_settings()

    def load_settings(self) -> Settings:
        """Load settings from file or create defaults"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    return Settings(**data)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                return Settings()
        else:
            # Create default settings
            default_settings = Settings()
            self.save_settings(default_settings)
            return default_settings

    def save_settings(self, settings: Settings) -> None:
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings.dict(), f, indent=2)
            self.settings = settings
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise

    def get_settings(self) -> Settings:
        """Get current settings"""
        return self.settings

    def update_settings(self, settings: Settings) -> Settings:
        """Update and save settings"""
        self.save_settings(settings)

        # Also update legacy company_config.json for backward compatibility
        self._update_legacy_configs(settings)

        return settings

    def _update_legacy_configs(self, settings: Settings) -> None:
        """Update legacy configuration files for backward compatibility"""
        # Update company_config.json
        company_config = {
            "name": settings.company_profile.name,
            "description": settings.company_profile.description,
            "capabilities": settings.company_profile.capabilities,
            "certifications": settings.company_profile.certifications,
            "differentiators": settings.company_profile.differentiators,
            "naics_codes": settings.company_profile.naics_codes,
            "cage_code": settings.company_profile.cage_code,
            "sam_uei": settings.company_profile.sam_uei
        }

        try:
            with open("company_config.json", 'w') as f:
                json.dump(company_config, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not update legacy company_config.json: {e}")

        # Update winning_rfps.txt
        if settings.company_profile.past_performance:
            try:
                with open("data/winning_rfps.txt", 'w') as f:
                    f.write('\n'.join(settings.company_profile.past_performance))
            except Exception as e:
                logger.warning(f"Could not update legacy winning_rfps.txt: {e}")

    def get_sam_api_key(self) -> Optional[str]:
        """Get SAM.gov API key"""
        key = self.settings.api_keys.sam_gov_api_key
        return key if key else None

    def get_google_credentials(self) -> Optional[dict]:
        """Get Google service account credentials"""
        json_str = self.settings.api_keys.google_service_account_json
        if not json_str:
            return None

        try:
            return json.loads(json_str)
        except:
            return None

    def get_google_sheets_id(self) -> Optional[str]:
        """Get Google Sheets ID"""
        sheet_id = self.settings.api_keys.google_sheets_id
        return sheet_id if sheet_id else None

    def validate_settings(self) -> dict:
        """Validate current settings and return status"""
        validation = {
            "sam_api_configured": bool(self.settings.api_keys.sam_gov_api_key),
            "google_sheets_configured": bool(
                self.settings.api_keys.google_service_account_json and
                self.settings.api_keys.google_sheets_id
            ),
            "company_profile_complete": bool(
                self.settings.company_profile.name and
                self.settings.company_profile.capabilities and
                self.settings.company_profile.naics_codes
            )
        }

        validation["all_configured"] = all(validation.values())
        return validation


# Singleton instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """Get singleton settings service instance"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service