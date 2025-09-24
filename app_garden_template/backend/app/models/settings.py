"""Settings models for RFP Discovery System"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class GoogleSheetsConfig(BaseModel):
    """Configuration for RFP workflow sheets"""
    qualified_sheet_id: str = Field(default="", description="Main findings - qualified RFPs to pursue")
    maybe_sheet_id: str = Field(default="", description="Maybe pile - RFPs needing further review")
    rejected_sheet_id: str = Field(default="", description="Rejected/spam - irrelevant RFPs")
    graveyard_sheet_id: str = Field(default="", description="Graveyard - lost/expired opportunities")
    bank_sheet_id: str = Field(default="", description="Bank - historical RFP data for analysis")


class APIKeys(BaseModel):
    """API keys and integration settings"""
    sam_gov_api_key: str = Field(default="", description="SAM.gov API key for searching federal opportunities")
    google_service_account_json: str = Field(default="", description="Google Service Account JSON for Sheets access")
    google_sheets: GoogleSheetsConfig = Field(default_factory=GoogleSheetsConfig, description="Google Sheets configuration")


class PastPerformanceEntry(BaseModel):
    """Detailed past performance entry"""
    contract_value: str = Field(default="", description="Contract value (e.g., $2.5M)")
    client: str = Field(default="", description="Client organization")
    title: str = Field(default="", description="Project title")
    description: str = Field(default="", description="Detailed description of work performed")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    outcomes: str = Field(default="", description="Key outcomes and achievements")
    year: str = Field(default="", description="Year of performance")


class CompanyProfile(BaseModel):
    """Company profile information for RFP matching"""
    name: str = Field(default="", description="Company name")
    description: str = Field(default="", description="Company description")
    capabilities: List[str] = Field(default_factory=list, description="Core capabilities and services")
    certifications: List[str] = Field(default_factory=list, description="Certifications and accreditations")
    differentiators: List[str] = Field(default_factory=list, description="Key differentiators and strengths")
    naics_codes: List[str] = Field(default_factory=list, description="NAICS codes")
    cage_code: str = Field(default="", description="CAGE code")
    sam_uei: str = Field(default="", description="SAM Unique Entity ID")
    past_performance: List[str] = Field(default_factory=list, description="Past performance summary (legacy)")
    detailed_past_performance: List[PastPerformanceEntry] = Field(
        default_factory=list,
        description="Detailed past performance with rich context"
    )
    target_rfp_examples: str = Field(
        default="",
        description="Detailed examples of ideal target RFPs with full context"
    )
    technical_approach_templates: str = Field(
        default="",
        description="Standard technical approaches and methodologies"
    )
    pricing_strategies: str = Field(
        default="",
        description="Typical pricing strategies and cost structures"
    )


class Settings(BaseModel):
    """Complete settings for RFP Discovery System"""
    api_keys: APIKeys = Field(default_factory=APIKeys)
    company_profile: CompanyProfile = Field(default_factory=CompanyProfile)