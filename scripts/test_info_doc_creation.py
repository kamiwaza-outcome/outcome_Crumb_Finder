#!/usr/bin/env python3
"""Test info doc creation with sample data"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.drive_manager import DriveManager

# Sample opportunity data
opportunity = {
    'title': 'RFI AI + DPA Business Process Flow Improvement Solution',
    'noticeId': '7e833ee2047242faa81f996e1ad80b29',
    'solicitationNumber': 'VA_RFI_SOO_AI_DPA_Business+Process+Flow+Improvement+Pilot',
    'type': 'Sources Sought',
    'postedDate': '2025-09-11',
    'responseDeadline': '2025-09-25 16:00:00',
    'archiveDate': '2025-10-25',
    'status': 'Active',
    'agency': 'Department of Veterans Affairs',
    'office': 'Office of Information and Technology',
    'location': 'Washington, DC',
    'naicsCode': '541512',
    'naicsDescription': 'Computer Systems Design Services',
    'pscCode': 'D399',
    'pscDescription': 'IT and Telecom - Other IT and Telecommunications',
    'setAside': 'N/A',
    'description': '''The Department of Veterans Affairs (VA) Office of Information and Technology (OIT) is seeking information from industry regarding Artificial Intelligence (AI) solutions to improve business process flows, specifically focusing on Discharge Planning Appointments (DPA) workflows.

This RFI seeks to understand available AI capabilities for:
- Process automation and optimization
- Workflow analysis and improvement
- Natural language processing for appointment scheduling
- Predictive analytics for resource allocation
- Integration with existing VA systems

Vendors should demonstrate experience with:
- Healthcare IT implementations
- AI/ML model deployment in production environments
- Federal compliance requirements (FISMA, FedRAMP)
- Large-scale data processing
- Real-time decision support systems''',
    'additionalInfoLink': 'https://sam.gov/opp/7e833ee2047242faa81f996e1ad80b29/view',
    'pointOfContact': {
        'name': 'Contracting Officer',
        'email': 'contracting@va.gov',
        'phone': '202-555-0100'
    },
    'instructions': 'Responses should be submitted via email by the deadline. Include company capabilities, past performance, and technical approach.',
    'evaluationCriteria': 'Responses will be evaluated based on technical capability, past performance, and understanding of VA requirements.',
    'placeOfPerformance': {
        'city': 'Washington',
        'state': 'DC',
        'country': 'USA'
    }
}

# Test folder ID from an actual RFP
folder_id = '1EnTbxyYJqs9h6hOC1eezKtnnVoYgxlbD'

drive_manager = DriveManager(Config.GOOGLE_SHEETS_CREDS_PATH)

print("Creating comprehensive info document...")
info_doc_link = drive_manager.create_info_document(opportunity, folder_id)

if info_doc_link:
    print(f"✅ Successfully created info doc!")
    print(f"📄 Document link: {info_doc_link}")
else:
    print("❌ Failed to create info doc")