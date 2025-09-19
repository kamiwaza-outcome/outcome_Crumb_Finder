"""
RFP Discovery Models for Request/Response validation
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RunStatus(str, Enum):
    """Status of an RFP discovery run"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunMode(str, Enum):
    """Run modes for RFP discovery"""
    TEST = "test"           # Quick test run with minimal processing
    NORMAL = "normal"       # Standard processing
    OVERKILL = "overkill"   # Maximum depth analysis


class QualificationLevel(str, Enum):
    """RFP qualification levels"""
    QUALIFIED = "qualified"     # Score 7-10
    MAYBE = "maybe"             # Score 4-6
    REJECTED = "rejected"       # Score 1-3


class RFPSearchRequest(BaseModel):
    """Request to search for RFPs"""
    search_keywords: List[str] = Field(
        default=['artificial intelligence', 'machine learning', 'data analytics'],
        description="Keywords to search for in RFPs"
    )
    days_back: int = Field(
        default=3,
        ge=1,
        le=30,
        description="Number of days to search back from today"
    )
    max_rfps: int = Field(
        default=200,
        ge=1,
        le=20000,
        description="Maximum number of RFPs to process"
    )
    model_name: str = Field(
        ...,
        description="Kamiwaza model to use for analysis"
    )
    run_mode: RunMode = Field(
        default=RunMode.NORMAL,
        description="Processing mode - test for quick runs, normal for standard, overkill for deep analysis"
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        le=128,
        description="Number of RFPs to process concurrently"
    )
    include_naics: Optional[List[str]] = Field(
        default=['541511', '541512', '541519', '518210'],
        description="NAICS codes to include"
    )
    exclude_keywords: Optional[List[str]] = Field(
        default=['janitorial', 'food service', 'construction'],
        description="Keywords to exclude from search"
    )


class RFPOpportunity(BaseModel):
    """Individual RFP opportunity"""
    notice_id: str = Field(..., description="Unique notice ID from SAM.gov")
    solicitation_number: Optional[str] = Field(None, description="Solicitation number")
    title: str = Field(..., description="RFP title")
    agency: str = Field(..., description="Issuing agency")
    description: str = Field(..., description="Full RFP description")
    posted_date: datetime = Field(..., description="Date RFP was posted")
    response_deadline: Optional[datetime] = Field(None, description="Response deadline")
    naics_code: Optional[str] = Field(None, description="Primary NAICS code")
    set_aside: Optional[str] = Field(None, description="Set-aside type (8a, SDVOSB, etc)")
    place_of_performance: Optional[str] = Field(None, description="Location of work")
    url: str = Field(..., description="Link to full RFP on SAM.gov")


class RFPAssessment(BaseModel):
    """AI assessment of an RFP"""
    is_qualified: bool = Field(..., description="Whether company should pursue")
    qualification_level: QualificationLevel = Field(..., description="Qualification tier")
    relevance_score: float = Field(..., ge=0, le=10, description="Match score 0-10")
    justification: str = Field(..., description="Why this is/isn't a fit")
    key_requirements: List[str] = Field(..., description="Key RFP requirements")
    company_advantages: List[str] = Field(..., description="Company strengths for this RFP")
    suggested_approach: str = Field(..., description="How to approach this RFP")
    ai_application: str = Field(..., description="How AI/ML applies to this RFP")
    uncertainty_factors: Optional[List[str]] = Field(None, description="Risks or uncertainties")
    similar_past_rfps: Optional[List[str]] = Field(None, description="Similar past wins")
    model_used: str = Field(..., description="Which Kamiwaza model was used")
    processing_time_ms: int = Field(..., description="Time to process in milliseconds")


class ProcessedRFP(BaseModel):
    """Fully processed RFP with assessment"""
    opportunity: RFPOpportunity
    assessment: RFPAssessment
    google_sheet_row: Optional[int] = Field(None, description="Row number in Google Sheet")
    drive_folder_id: Optional[str] = Field(None, description="Google Drive folder ID")
    drive_folder_url: Optional[str] = Field(None, description="Google Drive folder URL")


class RFPDiscoveryRun(BaseModel):
    """Complete discovery run with all RFPs"""
    run_id: str = Field(..., description="Unique run ID")
    started_at: datetime = Field(..., description="When run started")
    completed_at: Optional[datetime] = Field(None, description="When run completed")
    status: RunStatus = Field(..., description="Current run status")

    # Configuration
    search_config: RFPSearchRequest = Field(..., description="Search configuration used")

    # Results
    total_found: int = Field(0, description="Total RFPs found from sources")
    total_processed: int = Field(0, description="RFPs successfully processed")
    total_qualified: int = Field(0, description="RFPs marked as qualified (7-10)")
    total_maybe: int = Field(0, description="RFPs marked as maybe (4-6)")
    total_rejected: int = Field(0, description="RFPs marked as rejected (1-3)")
    total_errors: int = Field(0, description="RFPs that failed processing")

    # Processed RFPs by category
    qualified_rfps: List[ProcessedRFP] = Field(default_factory=list, description="Qualified RFPs")
    maybe_rfps: List[ProcessedRFP] = Field(default_factory=list, description="Maybe RFPs")
    rejected_rfps: List[ProcessedRFP] = Field(default_factory=list, description="Rejected RFPs")

    # Metadata
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")
    sheets_updated: Dict[str, bool] = Field(
        default_factory=dict,
        description="Which Google Sheets were updated"
    )


class RFPSchedule(BaseModel):
    """Schedule configuration for automated runs"""
    schedule_id: str = Field(..., description="Unique schedule ID")
    name: str = Field(..., description="Schedule name")
    run_mode: RunMode = Field(
        default=RunMode.NORMAL,
        description="Processing mode for this schedule"
    )
    cron_expression: str = Field(
        default="0 17 * * *",
        description="Cron expression (default: 5PM daily)"
    )
    enabled: bool = Field(True, description="Whether schedule is active")
    search_config: RFPSearchRequest = Field(..., description="Search configuration to use")
    last_run: Optional[datetime] = Field(None, description="Last successful run")
    next_run: Optional[datetime] = Field(None, description="Next scheduled run")


class DaemonStatus(BaseModel):
    """Current status of the RFP daemon"""
    is_running: bool = Field(..., description="Whether daemon is active")
    uptime_seconds: float = Field(..., description="Seconds since daemon started")
    current_run: Optional[RFPDiscoveryRun] = Field(None, description="Currently running discovery")
    recent_runs: List[RFPDiscoveryRun] = Field(
        default_factory=list,
        description="Last 10 completed runs"
    )
    active_schedules: List[RFPSchedule] = Field(
        default_factory=list,
        description="Active schedules"
    )
    system_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="CPU, memory, etc"
    )


class RFPLogEntry(BaseModel):
    """Single log entry from a run"""
    timestamp: datetime = Field(..., description="When log was created")
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR)")
    message: str = Field(..., description="Log message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class RFPRunLogs(BaseModel):
    """Logs for a specific run"""
    run_id: str = Field(..., description="Run ID")
    entries: List[RFPLogEntry] = Field(..., description="Log entries")
    total_entries: int = Field(..., description="Total number of log entries")