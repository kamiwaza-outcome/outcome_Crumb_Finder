"""Google Sheets integration service for RFP tracking"""

import logging
import json
import hashlib
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import ssl
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.models.rfp import RFP
from app.models.settings import Settings

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((ssl.SSLError, ConnectionError, TimeoutError, HttpError))
)
def execute_with_retry(request):
    """Execute a Google API request with retry logic for network errors"""
    return request.execute()


class SheetsService:
    """Service for managing Google Sheets integration"""

    def __init__(self, settings: Settings):
        """Initialize sheets service with settings"""
        self.settings = settings
        self.service = None
        self.credentials = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Sheets service if credentials are available"""
        try:
            service_account_json = self.settings.api_keys.google_service_account_json
            if not service_account_json:
                logger.info("No Google service account configured")
                return

            # Parse JSON credentials
            if isinstance(service_account_json, str):
                if service_account_json.startswith('{'):
                    # It's already JSON string
                    creds_dict = json.loads(service_account_json)
                else:
                    # It might be a file path
                    try:
                        with open(service_account_json, 'r') as f:
                            creds_dict = json.load(f)
                    except:
                        logger.error("Invalid service account JSON format")
                        return
            else:
                creds_dict = service_account_json

            self.credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )

            self.service = build('sheets', 'v4', credentials=self.credentials)
            logger.info("Google Sheets service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            self.service = None

    def is_configured(self) -> bool:
        """Check if Google Sheets integration is configured"""
        return self.service is not None

    def get_sheet_headers(self) -> List[str]:
        """Get standard headers for RFP tracking sheets"""
        return [
            'Source/URL',
            'Title',
            'Agency',
            'Posted Date',
            'Due Date',
            'Estimated Value',
            'NAICS',
            'Location',
            'AI Score',
            'AI Justification',
            'Key Requirements',
            'Suggested Approach',
            'Status',
            'Notice ID',
            'Date Added'
        ]

    def setup_sheet_if_needed(self, sheet_id: str, sheet_type: str) -> bool:
        """Setup headers in sheet if it's empty"""
        if not self.is_configured():
            return False

        try:
            # Check if sheet has headers
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:O1'
            ).execute()

            if not result.get('values'):
                # Sheet is empty, add headers
                headers = [self.get_sheet_headers()]

                request = self.service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range='A1:O1',
                    valueInputOption='USER_ENTERED',
                    body={'values': headers}
                )
                execute_with_retry(request)

                logger.info(f"Added headers to {sheet_type} sheet {sheet_id}")
                return True

            return True

        except Exception as e:
            logger.error(f"Failed to setup sheet {sheet_id}: {str(e)}")
            return False

    def get_existing_notice_ids(self, sheet_id: str) -> Set[str]:
        """Get all existing Notice IDs from a sheet for duplicate detection"""
        if not self.is_configured():
            return set()

        try:
            # Get Notice ID column (column N, 14th column)
            request = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='N:N'
            )
            result = execute_with_retry(request)

            values = result.get('values', [])
            notice_ids = set()

            # Skip header row
            for row in values[1:]:
                if row and row[0]:
                    notice_ids.add(str(row[0]).strip())

            logger.info(f"Found {len(notice_ids)} existing Notice IDs in sheet {sheet_id}")
            return notice_ids

        except Exception as e:
            logger.warning(f"Could not read Notice IDs from {sheet_id}: {str(e)}")
            return set()

    def add_rfp_to_sheet(self, rfp: RFP, sheet_id: str, sheet_type: str) -> bool:
        """Add an RFP to the specified Google Sheet"""
        if not self.is_configured() or not sheet_id:
            logger.info(f"Skipping sheet update - not configured or no sheet ID for {sheet_type}")
            return False

        try:
            # Prepare row data
            row_data = [[
                rfp.url or '',  # Source/URL
                (rfp.title or '')[:200],  # Title (truncated)
                rfp.agency or '',  # Agency
                rfp.posted_date or '',  # Posted Date
                rfp.response_deadline or '',  # Due Date
                '',  # Estimated Value (not in RFP model)
                rfp.naics_code or '',  # NAICS
                '',  # Location (not in RFP model)
                str(rfp.ai_score) if rfp.ai_score else '',  # AI Score
                (rfp.ai_justification or '')[:500],  # AI Justification (truncated)
                ', '.join(rfp.key_requirements or [])[:300],  # Key Requirements
                (rfp.suggested_approach or '')[:300],  # Suggested Approach
                sheet_type.capitalize(),  # Status (based on sheet type)
                rfp.notice_id or '',  # Notice ID
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Date Added
            ]]

            # Append to sheet
            request = self.service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='A:O',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': row_data}
            )
            execute_with_retry(request)

            logger.info(f"Added RFP {rfp.notice_id} to {sheet_type} sheet")
            return True

        except Exception as e:
            logger.error(f"Failed to add RFP to {sheet_type} sheet: {str(e)}")
            return False

    def push_qualified_rfps(self, rfps: List[RFP]) -> Dict[str, int]:
        """Push qualified RFPs to appropriate sheets"""
        if not self.is_configured():
            logger.info("Google Sheets not configured - skipping push")
            return {'qualified': 0, 'maybe': 0, 'rejected': 0}

        sheets_config = self.settings.api_keys.google_sheets
        results = {'qualified': 0, 'maybe': 0, 'rejected': 0}

        # Setup sheets if needed
        if sheets_config.qualified_sheet_id:
            self.setup_sheet_if_needed(sheets_config.qualified_sheet_id, 'qualified')
        if sheets_config.maybe_sheet_id:
            self.setup_sheet_if_needed(sheets_config.maybe_sheet_id, 'maybe')
        if sheets_config.rejected_sheet_id:
            self.setup_sheet_if_needed(sheets_config.rejected_sheet_id, 'rejected')

        # Get existing Notice IDs to avoid duplicates
        qualified_existing = set()
        maybe_existing = set()
        rejected_existing = set()

        if sheets_config.qualified_sheet_id:
            qualified_existing = self.get_existing_notice_ids(sheets_config.qualified_sheet_id)
        if sheets_config.maybe_sheet_id:
            maybe_existing = self.get_existing_notice_ids(sheets_config.maybe_sheet_id)
        if sheets_config.rejected_sheet_id:
            rejected_existing = self.get_existing_notice_ids(sheets_config.rejected_sheet_id)

        # Process each RFP
        for rfp in rfps:
            # Skip if already in any sheet
            if rfp.notice_id in qualified_existing or \
               rfp.notice_id in maybe_existing or \
               rfp.notice_id in rejected_existing:
                logger.info(f"Skipping duplicate RFP {rfp.notice_id}")
                continue

            # Determine which sheet based on AI score
            if rfp.ai_score >= 7:
                # High score - qualified
                if sheets_config.qualified_sheet_id:
                    if self.add_rfp_to_sheet(rfp, sheets_config.qualified_sheet_id, 'qualified'):
                        results['qualified'] += 1
            elif rfp.ai_score >= 4:
                # Medium score - maybe
                if sheets_config.maybe_sheet_id:
                    if self.add_rfp_to_sheet(rfp, sheets_config.maybe_sheet_id, 'maybe'):
                        results['maybe'] += 1
            else:
                # Low score - rejected
                if sheets_config.rejected_sheet_id:
                    if self.add_rfp_to_sheet(rfp, sheets_config.rejected_sheet_id, 'rejected'):
                        results['rejected'] += 1

        logger.info(f"Pushed RFPs to sheets - Qualified: {results['qualified']}, "
                   f"Maybe: {results['maybe']}, Rejected: {results['rejected']}")

        return results

    def add_to_graveyard(self, rfp: RFP) -> bool:
        """Add expired or lost RFP to graveyard sheet"""
        if not self.is_configured():
            return False

        graveyard_sheet_id = self.settings.api_keys.google_sheets.graveyard_sheet_id
        if not graveyard_sheet_id:
            return False

        self.setup_sheet_if_needed(graveyard_sheet_id, 'graveyard')
        return self.add_rfp_to_sheet(rfp, graveyard_sheet_id, 'graveyard')

    def add_to_bank(self, rfp: RFP) -> bool:
        """Add RFP to bank sheet for historical reference"""
        if not self.is_configured():
            return False

        bank_sheet_id = self.settings.api_keys.google_sheets.bank_sheet_id
        if not bank_sheet_id:
            return False

        self.setup_sheet_if_needed(bank_sheet_id, 'bank')
        return self.add_rfp_to_sheet(rfp, bank_sheet_id, 'bank')

    def format_sheet_headers(self, sheet_id: str) -> bool:
        """Apply formatting to sheet headers"""
        if not self.is_configured():
            return False

        try:
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True, 'fontSize': 11},
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat'
                }
            }]

            request = self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            )
            execute_with_retry(request)

            logger.info(f"Formatted headers for sheet {sheet_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to format sheet headers: {str(e)}")
            return False