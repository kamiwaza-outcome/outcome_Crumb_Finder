import os
import io
import logging
import zipfile
import re
import requests
import json
from datetime import datetime
from typing import Optional, List, Dict
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from config import Config
from src.sanitizer import Sanitizer

logger = logging.getLogger(__name__)

class DriveManager:
    def __init__(self, service_account_path: str):
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            # Initialize session for fetching descriptions
            self.session = requests.Session()
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {str(e)}")
            raise
    
    def create_folder(self, name: str, parent_id: str = None) -> str:
        """Create a folder in Google Drive"""
        
        # Sanitize folder name properly
        clean_name = Sanitizer.sanitize_filename(name)
        if not clean_name:
            clean_name = 'unnamed_rfp_folder'
        
        # Use Daily RFPs folder as default parent if no parent specified
        if not parent_id and Config.DAILY_RFPS_FOLDER_ID:
            parent_id = Config.DAILY_RFPS_FOLDER_ID
            logger.info(f"Using Daily RFPs folder as parent: {parent_id}")
        
        folder_metadata = {
            'name': clean_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        try:
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            if not folder_id:
                logger.error("Folder created but no ID returned")
                return None
            
            logger.info(f"Created folder: {clean_name} with ID: {folder_id}")
            return folder_id
            
        except Exception as e:
            logger.error(f"Failed to create folder: {str(e)}")
            return None  # Return None instead of raising to prevent data loss
    
    def get_folder_url(self, folder_id: str) -> str:
        """Get the Google Drive URL for a folder"""
        return f"https://drive.google.com/drive/folders/{folder_id}"

    def upload_file(self, file_content: bytes, filename: str, folder_id: str, mimetype: str = 'application/octet-stream') -> Optional[str]:
        """Upload a file to Google Drive"""
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        try:
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mimetype,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            logger.info(f"Uploaded file: {filename} with ID: {file.get('id')}")
            return file.get('id')
            
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {str(e)}")
            return None
    
    def download_and_store(self, url: str, folder_id: str, session: requests.Session = None, api_key: str = None) -> Optional[str]:
        """Download file from URL and store in Drive"""

        if not session:
            session = requests.Session()

        try:
            # For SAM.gov URLs, add API key as parameter
            if 'sam.gov' in url and api_key:
                # Add API key to URL parameters
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}api_key={api_key}"

            # Download the file
            response = session.get(url, timeout=60)
            response.raise_for_status()
            
            # Get filename from URL or Content-Disposition header
            filename = None
            if 'Content-Disposition' in response.headers:
                cd = response.headers['Content-Disposition']
                filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', cd)
                if filename_match:
                    filename = filename_match.group(1).strip('"\'')
            
            if not filename:
                # Extract from URL
                filename = url.split('/')[-1].split('?')[0]
                if not filename:
                    filename = 'attachment'
            
            # Sanitize filename
            filename = Sanitizer.sanitize_filename(filename)
            
            # Determine mimetype
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            
            # Upload to Drive
            file_id = self.upload_file(
                response.content,
                filename,
                folder_id,
                content_type
            )
            
            if file_id:
                logger.info(f"Successfully stored {filename} in Drive")
                return file_id
            
        except Exception as e:
            logger.error(f"Failed to download and store from {url}: {str(e)}")
            
        return None
    
    def process_rfp_attachments(self, attachments: List[Dict], folder_id: str, session: requests.Session = None, api_key: str = None) -> List[str]:
        """Process and store multiple RFP attachments"""

        if not session:
            session = requests.Session()

        stored_files = []

        for attachment in attachments:
            url = attachment.get('url')
            if not url:
                continue

            try:
                file_id = self.download_and_store(url, folder_id, session, api_key)
                if file_id:
                    stored_files.append(file_id)
                    logger.info(f"Processed attachment: {attachment.get('name', 'unknown')}")

            except Exception as e:
                logger.error(f"Failed to process attachment: {str(e)}")
                continue
        
        logger.info(f"Processed {len(stored_files)} of {len(attachments)} attachments")
        
        # Special handling for high-value RFPs (many attachments)
        if len(attachments) > 10:
            logger.info(f"High-value RFP with {len(attachments)} attachments - all stored in Drive folder")
            
        # Return list of stored files
        return stored_files
    
    def _fetch_description_from_api(self, description_url: str, api_key: str) -> str:
        """Fetch the full description text from SAM.gov API"""
        try:
            # Add API key to the URL
            if '?' in description_url:
                full_url = f"{description_url}&api_key={api_key}"
            else:
                full_url = f"{description_url}?api_key={api_key}"
            
            response = self.session.get(full_url, timeout=30)
            response.raise_for_status()
            
            # The API returns HTML content
            content = response.text
            
            # Basic HTML tag removal (for plain text extraction)
            # Remove script and style elements
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', ' ', content)
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()
            
            return content if content else "No description content available"
            
        except Exception as e:
            logger.error(f"Failed to fetch description from {description_url}: {str(e)}")
            return f"Failed to fetch description: {str(e)}"
    
    def create_info_document(self, opportunity: Dict, folder_id: str) -> Optional[str]:
        """Create a comprehensive Google Doc with all RFP information"""
        try:
            # Build the document content with ALL available data
            doc_content = self._build_comprehensive_doc(opportunity)
            
            # Create the Google Doc
            doc_metadata = {
                'name': f"{opportunity.get('title', 'RFP Info')[:100]} - Complete Information",
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [folder_id]
            }
            
            # Create empty doc first
            doc = self.service.files().create(
                body=doc_metadata,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            doc_id = doc.get('id')
            if not doc_id:
                logger.error("Document created but no ID returned")
                return None
            
            # Now update the doc with content using Google Docs API
            docs_service = build('docs', 'v1', credentials=self.credentials)
            
            # Create the document structure
            requests = [
                {
                    'insertText': {
                        'location': {'index': 1},
                        'text': doc_content
                    }
                }
            ]
            
            # Execute the update
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Created comprehensive info doc with ID: {doc_id}")
            return doc.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Failed to create info document: {str(e)}")
            return None

    def update_info_document(self, doc_id: str, opportunity: Dict, assessment: Dict = None) -> bool:
        """Update an existing Google Doc with new RFP information and AI assessment"""
        try:
            # Build the updated document content
            doc_content = self._build_comprehensive_doc(opportunity)

            # Add AI assessment if provided
            if assessment:
                doc_content += f"\n\n{'='*60}\n"
                doc_content += f"AI ASSESSMENT\n"
                doc_content += f"{'='*60}\n"
                doc_content += f"Relevance Score: {assessment.get('relevance_score', 'N/A')}/10\n"
                doc_content += f"Justification: {assessment.get('justification', 'N/A')}\n\n"

                if assessment.get('key_requirements'):
                    doc_content += f"Key Requirements:\n"
                    for req in assessment['key_requirements']:
                        doc_content += f"  • {req}\n"
                    doc_content += "\n"

                if assessment.get('company_advantages'):
                    doc_content += f"Company Advantages:\n"
                    for adv in assessment['company_advantages']:
                        doc_content += f"  • {adv}\n"
                    doc_content += "\n"

                if assessment.get('suggested_approach'):
                    doc_content += f"Suggested Approach:\n{assessment['suggested_approach']}\n\n"

                if assessment.get('ai_application'):
                    doc_content += f"AI Applications:\n{assessment['ai_application']}\n\n"

            # Use Google Docs API to update the document
            docs_service = build('docs', 'v1', credentials=self.credentials)

            # First, clear the existing content
            document = docs_service.documents().get(documentId=doc_id).execute()
            content = document.get('body').get('content')

            # Find the end index
            end_index = content[-1]['endIndex'] - 1 if content else 1

            # Create requests to update the document
            requests = []

            # Delete existing content (except the first character)
            if end_index > 1:
                requests.append({
                    'deleteContentRange': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': end_index
                        }
                    }
                })

            # Insert new content
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': doc_content
                }
            })

            # Execute the update
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

            logger.info(f"Successfully updated info document: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update info document: {str(e)}")
            return False

    def _build_comprehensive_doc(self, opportunity: Dict) -> str:
        """Build comprehensive document content extracting ALL available data"""
        
        sections = []
        
        # Title and basic info
        sections.append(f"{'='*80}\n")
        sections.append(f"RFP COMPLETE INFORMATION DOCUMENT\n")
        sections.append(f"{'='*80}\n\n")
        
        # Basic Information
        sections.append(f"Title: {opportunity.get('title', 'N/A')}\n")
        sections.append(f"Notice ID: {opportunity.get('noticeId', 'N/A')}\n")
        sections.append(f"Solicitation Number: {opportunity.get('solicitationNumber', 'N/A')}\n")
        sections.append(f"Type: {opportunity.get('type', opportunity.get('baseType', 'N/A'))}\n")
        sections.append(f"Status: {opportunity.get('active', 'N/A')}\n\n")
        
        # Important Dates
        sections.append(f"{'='*60}\n")
        sections.append(f"IMPORTANT DATES\n")
        sections.append(f"{'='*60}\n")
        sections.append(f"Posted Date: {opportunity.get('postedDate', 'N/A')}\n")
        sections.append(f"Response Deadline: {opportunity.get('responseDeadLine', opportunity.get('responseDeadline', 'N/A'))}\n")
        sections.append(f"Archive Date: {opportunity.get('archiveDate', 'N/A')}\n")
        sections.append(f"Archive Type: {opportunity.get('archiveType', 'N/A')}\n\n")
        
        # Organization/Agency Information - Extract from hierarchy
        sections.append(f"{'='*60}\n")
        sections.append(f"ORGANIZATION INFORMATION\n")
        sections.append(f"{'='*60}\n")
        
        # Parse the full parent path for agency hierarchy
        if opportunity.get('fullParentPathName'):
            hierarchy = opportunity['fullParentPathName'].split('.')
            if len(hierarchy) > 0:
                sections.append(f"Department: {hierarchy[0].strip()}\n")
            if len(hierarchy) > 1:
                sections.append(f"Agency: {hierarchy[1].strip()}\n")
            if len(hierarchy) > 2:
                sections.append(f"Sub-Agency/Office: {hierarchy[2].strip()}\n")
        
        sections.append(f"Organization Type: {opportunity.get('organizationType', 'N/A')}\n")
        sections.append(f"Organization Code: {opportunity.get('fullParentPathCode', 'N/A')}\n")
        
        # Office Address
        if opportunity.get('officeAddress'):
            addr = opportunity['officeAddress']
            sections.append(f"\nOffice Address:\n")
            sections.append(f"  City: {addr.get('city', 'N/A')}\n")
            sections.append(f"  State: {addr.get('state', 'N/A')}\n")
            sections.append(f"  Zip Code: {addr.get('zipcode', 'N/A')}\n")
            sections.append(f"  Country: {addr.get('countryCode', 'N/A')}\n")
        sections.append("\n")
        
        # Classification Codes with descriptions
        sections.append(f"{'='*60}\n")
        sections.append(f"CLASSIFICATION CODES\n")
        sections.append(f"{'='*60}\n")
        
        # NAICS Codes
        sections.append(f"NAICS Code: {opportunity.get('naicsCode', 'N/A')}\n")
        if opportunity.get('naicsCodes'):
            sections.append("NAICS Details:\n")
            for naics in opportunity['naicsCodes']:
                if isinstance(naics, dict):
                    sections.append(f"  Code: {naics.get('code', 'N/A')}\n")
                    sections.append(f"  Description: {naics.get('description', 'N/A')}\n")
                elif isinstance(naics, str):
                    sections.append(f"  {naics}\n")
        
        # PSC/Classification Code
        sections.append(f"\nProduct/Service Code: {opportunity.get('classificationCode', opportunity.get('pscCode', 'N/A'))}\n")
        sections.append(f"PSC Description: {opportunity.get('pscDescription', opportunity.get('classificationDescription', 'N/A'))}\n\n")
        
        # Set-Aside Information
        sections.append(f"{'='*60}\n")
        sections.append(f"SET-ASIDE INFORMATION\n")
        sections.append(f"{'='*60}\n")
        sections.append(f"Set-Aside Type: {opportunity.get('typeOfSetAside', 'N/A')}\n")
        sections.append(f"Set-Aside Description: {opportunity.get('typeOfSetAsideDescription', 'N/A')}\n\n")
        
        # Award Information (if available)
        if opportunity.get('award'):
            sections.append(f"{'='*60}\n")
            sections.append(f"AWARD INFORMATION\n")
            sections.append(f"{'='*60}\n")
            award = opportunity['award']
            if isinstance(award, dict):
                sections.append(f"Awardee: {award.get('awardee', 'N/A')}\n")
                sections.append(f"Award Amount: {award.get('amount', 'N/A')}\n")
                sections.append(f"Award Date: {award.get('date', 'N/A')}\n")
                sections.append(f"Award Number: {award.get('number', 'N/A')}\n")
            sections.append("\n")
        
        # Place of Performance
        sections.append(f"{'='*60}\n")
        sections.append(f"PLACE OF PERFORMANCE\n")
        sections.append(f"{'='*60}\n")
        if opportunity.get('placeOfPerformance'):
            pop = opportunity['placeOfPerformance']
            if isinstance(pop, dict):
                # Handle nested city/state/country objects
                city_info = pop.get('city', {})
                state_info = pop.get('state', {})
                country_info = pop.get('country', {})
                
                if isinstance(city_info, dict):
                    sections.append(f"City: {city_info.get('name', city_info.get('code', 'N/A'))}\n")
                else:
                    sections.append(f"City: {city_info or 'N/A'}\n")
                    
                if isinstance(state_info, dict):
                    sections.append(f"State: {state_info.get('name', state_info.get('code', 'N/A'))}\n")
                else:
                    sections.append(f"State: {state_info or 'N/A'}\n")
                    
                if isinstance(country_info, dict):
                    sections.append(f"Country: {country_info.get('name', country_info.get('code', 'N/A'))}\n")
                else:
                    sections.append(f"Country: {country_info or 'N/A'}\n")
                    
                sections.append(f"Zip Code: {pop.get('zip', 'N/A')}\n")
        else:
            sections.append("Not specified\n")
        sections.append("\n")
        
        # Full Description - FETCH FROM API IF IT'S A URL
        sections.append(f"{'='*60}\n")
        sections.append(f"FULL DESCRIPTION\n")
        sections.append(f"{'='*60}\n")
        
        description = opportunity.get('description', '')
        if description and description.startswith('http'):
            # It's a URL - fetch the actual description
            logger.info(f"Fetching full description from API: {description}")
            api_key = Config.SAM_API_KEY if hasattr(Config, 'SAM_API_KEY') else ''
            full_description = self._fetch_description_from_api(description, api_key)
            sections.append(f"{full_description}\n\n")
        elif description:
            sections.append(f"{description}\n\n")
        else:
            sections.append("No description available\n\n")
        
        # Point of Contact - Handle list of contacts
        sections.append(f"{'='*60}\n")
        sections.append(f"POINT OF CONTACT\n")
        sections.append(f"{'='*60}\n")
        
        if opportunity.get('pointOfContact'):
            poc = opportunity['pointOfContact']
            if isinstance(poc, list):
                for i, contact in enumerate(poc, 1):
                    if len(poc) > 1:
                        sections.append(f"\nContact {i}:\n")
                    sections.append(f"  Name: {contact.get('fullName', contact.get('name', 'N/A'))}\n")
                    sections.append(f"  Title: {contact.get('title', 'N/A')}\n")
                    sections.append(f"  Email: {contact.get('email', 'N/A')}\n")
                    sections.append(f"  Phone: {contact.get('phone', 'N/A')}\n")
                    if contact.get('fax'):
                        sections.append(f"  Fax: {contact['fax']}\n")
                    sections.append(f"  Type: {contact.get('type', 'N/A')}\n")
            elif isinstance(poc, dict):
                sections.append(f"Name: {poc.get('fullName', poc.get('name', 'N/A'))}\n")
                sections.append(f"Title: {poc.get('title', 'N/A')}\n")
                sections.append(f"Email: {poc.get('email', 'N/A')}\n")
                sections.append(f"Phone: {poc.get('phone', 'N/A')}\n")
                if poc.get('fax'):
                    sections.append(f"Fax: {poc['fax']}\n")
        else:
            sections.append("No contact information available\n")
        sections.append("\n")
        
        # Links and Resources
        sections.append(f"{'='*60}\n")
        sections.append(f"LINKS AND RESOURCES\n")
        sections.append(f"{'='*60}\n")
        
        # SAM.gov links
        default_link = f"https://sam.gov/opp/{opportunity.get('noticeId', 'unknown')}/view"
        sections.append(f"SAM.gov Link: {opportunity.get('uiLink', default_link)}\n")
        
        if opportunity.get('additionalInfoLink'):
            sections.append(f"Additional Info: {opportunity['additionalInfoLink']}\n")
        
        # Resource Links (attachments)
        if opportunity.get('resourceLinks'):
            sections.append("\nAttachments/Resources:\n")
            links = opportunity['resourceLinks']
            if isinstance(links, list):
                for i, link in enumerate(links, 1):
                    if isinstance(link, str):
                        sections.append(f"  {i}. {link}\n")
                    elif isinstance(link, dict):
                        sections.append(f"  {i}. {link.get('name', 'Attachment')} - {link.get('url', 'N/A')}\n")
        
        # Related links
        if opportunity.get('links'):
            sections.append("\nRelated Links:\n")
            for link in opportunity['links']:
                if isinstance(link, dict):
                    sections.append(f"  - {link.get('rel', 'Link')}: {link.get('href', 'N/A')}\n")
                else:
                    sections.append(f"  - {link}\n")
        
        sections.append("\n")
        
        # Additional fields that might be present
        additional_fields = [
            ('instructions', 'SUBMISSION INSTRUCTIONS'),
            ('evaluationCriteria', 'EVALUATION CRITERIA'),
            ('specialRequirements', 'SPECIAL REQUIREMENTS'),
            ('clauses', 'CLAUSES'),
            ('solicitation', 'SOLICITATION DETAILS'),
            ('modifications', 'MODIFICATIONS')
        ]
        
        for field_key, field_title in additional_fields:
            if opportunity.get(field_key):
                sections.append(f"{'='*60}\n")
                sections.append(f"{field_title}\n")
                sections.append(f"{'='*60}\n")
                sections.append(f"{opportunity[field_key]}\n\n")
        
        # Metadata footer
        sections.append(f"{'='*80}\n")
        sections.append(f"Document Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        sections.append(f"{'='*80}\n")
        
        return ''.join(sections)