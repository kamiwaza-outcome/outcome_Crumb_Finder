"""
RFP Discovery Service using Kamiwaza SDK for local model deployment
Replaces OpenAI API calls with locally deployed models
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.base_service import BaseService
from app.services.kamiwaza_service import KamiwazaService
from app.services.settings_service import get_settings_service
from app.models.rfp import (
    RFPOpportunity,
    RFPAssessment,
    ProcessedRFP,
    QualificationLevel,
    RFPDiscoveryRun,
    RunStatus,
    RFPSearchRequest
)
from app.core.errors import ServiceError, AIServiceError

logger = logging.getLogger(__name__)


class RFPDiscoveryService(BaseService):
    """Service for discovering and qualifying RFP opportunities using Kamiwaza models"""

    def __init__(self, kamiwaza_service: KamiwazaService):
        super().__init__(kamiwaza_service)
        self.settings_service = get_settings_service()
        self.company_profile = self._load_company_profile()
        self.past_rfps = self._load_past_rfps()

    async def process(self, request: Any) -> Any:
        """Required abstract method from BaseService"""
        # This is implemented through discover_rfps method
        pass

    def _load_company_profile(self) -> str:
        """Load company profile from settings"""
        settings = self.settings_service.get_settings()
        profile = settings.company_profile

        if not profile.name:
            return "Company profile not configured. Please configure in Settings."

        profile_text = f"""
Company: {profile.name}
Description: {profile.description}
Capabilities: {', '.join(profile.capabilities) if profile.capabilities else 'Not specified'}
Certifications: {', '.join(profile.certifications) if profile.certifications else 'Not specified'}
Differentiators: {', '.join(profile.differentiators) if profile.differentiators else 'Not specified'}
NAICS Codes: {', '.join(profile.naics_codes) if profile.naics_codes else 'Not specified'}
CAGE Code: {profile.cage_code or 'Not specified'}
SAM UEI: {profile.sam_uei or 'Not specified'}
"""
        return profile_text

    def _load_past_rfps(self) -> str:
        """Load past winning RFPs from settings"""
        settings = self.settings_service.get_settings()
        past_performance = settings.company_profile.past_performance

        if past_performance:
            return '\n'.join(past_performance)
        return "No past performance data configured"

    async def discover_rfps(self, request: RFPSearchRequest) -> RFPDiscoveryRun:
        """
        Main discovery method - searches for and evaluates RFPs

        This replaces the OpenAI-based discovery with Kamiwaza model calls
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = RFPDiscoveryRun(
            run_id=run_id,
            started_at=datetime.now(),
            status=RunStatus.RUNNING,
            search_config=request
        )

        try:
            # 1. Search for RFPs from SAM.gov
            logger.info(f"Starting RFP discovery run {run_id}")
            opportunities = await self._search_sam_gov(request)
            run.total_found = len(opportunities)

            # 2. Process in batches using Kamiwaza models
            processed_rfps = await self._process_opportunities_batch(
                opportunities,
                request.model_name,
                request.batch_size
            )

            # 3. Categorize results
            for rfp in processed_rfps:
                score = rfp.assessment.relevance_score
                if score >= 7:
                    rfp.assessment.qualification_level = QualificationLevel.QUALIFIED
                    run.qualified_rfps.append(rfp)
                    run.total_qualified += 1
                elif score >= 4:
                    rfp.assessment.qualification_level = QualificationLevel.MAYBE
                    run.maybe_rfps.append(rfp)
                    run.total_maybe += 1
                else:
                    rfp.assessment.qualification_level = QualificationLevel.REJECTED
                    run.rejected_rfps.append(rfp)
                    run.total_rejected += 1

            run.total_processed = len(processed_rfps)
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.now()
            run.processing_time_seconds = (
                run.completed_at - run.started_at
            ).total_seconds()

            logger.info(
                f"Discovery run {run_id} completed: "
                f"{run.total_qualified} qualified, "
                f"{run.total_maybe} maybe, "
                f"{run.total_rejected} rejected"
            )

        except Exception as e:
            logger.error(f"Discovery run {run_id} failed: {e}")
            run.status = RunStatus.FAILED
            run.errors.append({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            raise ServiceError(f"RFP discovery failed: {e}")

        return run

    async def _search_sam_gov(self, request: RFPSearchRequest) -> List[Dict[str, Any]]:
        """Search SAM.gov for opportunities"""
        # Check if SAM.gov API key is configured
        sam_api_key = self.settings_service.get_sam_api_key()

        if sam_api_key:
            # TODO: Implement real SAM.gov API integration
            logger.info("SAM.gov API key configured - would use real API")
            # For now, still return mock data
        else:
            logger.info("No SAM.gov API key configured - using mock data for demonstration")

        # Mock data for demonstration purposes
        mock_opportunities = [
            {
                "noticeId": "RFP-2025-001",
                "solicitationNumber": "FA8750-25-R-0001",
                "title": "Artificial Intelligence and Machine Learning Platform Development",
                "fullParentPathName": "Department of Defense / Air Force Research Laboratory",
                "description": "The Air Force Research Laboratory seeks an AI/ML platform for advanced data analytics and predictive modeling. The system must support large-scale data processing, real-time inference, and model training capabilities.",
                "postedDate": (datetime.now() - timedelta(days=2)).isoformat(),
                "responseDeadLine": (datetime.now() + timedelta(days=30)).isoformat(),
                "naicsCode": "541511",
                "typeOfSetAsideDescription": "Small Business",
                "placeOfPerformanceCity": "Wright-Patterson AFB, OH",
                "uiLink": "https://sam.gov/opp/RFP-2025-001/view"
            },
            {
                "noticeId": "RFP-2025-002",
                "solicitationNumber": "W15P7T-25-R-D003",
                "title": "Cloud Infrastructure Migration and Modernization Services",
                "fullParentPathName": "Department of the Army / CECOM",
                "description": "Seeking contractor support for migrating legacy applications to cloud infrastructure. Requirements include AWS/Azure expertise, containerization, and DevOps automation.",
                "postedDate": (datetime.now() - timedelta(days=1)).isoformat(),
                "responseDeadLine": (datetime.now() + timedelta(days=25)).isoformat(),
                "naicsCode": "541512",
                "typeOfSetAsideDescription": None,
                "placeOfPerformanceCity": "Fort Belvoir, VA",
                "uiLink": "https://sam.gov/opp/RFP-2025-002/view"
            },
            {
                "noticeId": "RFP-2025-003",
                "solicitationNumber": "HHS-NIH-NHLBI-25-001",
                "title": "Biomedical Data Analytics and Visualization Platform",
                "fullParentPathName": "Department of Health and Human Services / NIH",
                "description": "Development of a comprehensive data analytics platform for biomedical research data. Must support genomic data analysis, clinical trial data management, and interactive visualization.",
                "postedDate": (datetime.now() - timedelta(days=3)).isoformat(),
                "responseDeadLine": (datetime.now() + timedelta(days=21)).isoformat(),
                "naicsCode": "541511",
                "typeOfSetAsideDescription": "8(a)",
                "placeOfPerformanceCity": "Bethesda, MD",
                "uiLink": "https://sam.gov/opp/RFP-2025-003/view"
            }
        ]

        # Filter based on keywords
        filtered_opportunities = []
        for opp in mock_opportunities:
            for keyword in request.search_keywords:
                if keyword.lower() in opp["title"].lower() or keyword.lower() in opp["description"].lower():
                    filtered_opportunities.append(opp)
                    break

        # Limit to max_rfps
        all_opportunities = filtered_opportunities[:request.max_rfps]
        logger.info(f"Returning {len(all_opportunities)} mock opportunities for testing")

        # Deduplicate by notice ID
        unique = {}
        for opp in all_opportunities:
            notice_id = opp.get('noticeId')
            if notice_id and notice_id not in unique:
                # Filter out excluded keywords
                title = opp.get('title', '').lower()
                description = opp.get('description', '').lower()

                should_exclude = False
                for exclude_keyword in (request.exclude_keywords or []):
                    if exclude_keyword.lower() in title or exclude_keyword.lower() in description:
                        should_exclude = True
                        break

                if not should_exclude:
                    unique[notice_id] = opp

        opportunities = list(unique.values())[:request.max_rfps]
        logger.info(f"Found {len(opportunities)} unique opportunities after filtering")

        return opportunities

    async def _process_opportunities_batch(
        self,
        opportunities: List[Dict[str, Any]],
        model_name: str,
        batch_size: int
    ) -> List[ProcessedRFP]:
        """Process opportunities in batches using thread pool"""
        processed = []

        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all tasks
            futures = {
                executor.submit(
                    self._process_single_opportunity,
                    opp,
                    model_name
                ): opp
                for opp in opportunities
            }

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    if result:
                        processed.append(result)
                except Exception as e:
                    opp = futures[future]
                    logger.error(f"Failed to process RFP {opp.get('noticeId', 'unknown')}: {e}")

        return processed

    def _process_single_opportunity(
        self,
        opportunity: Dict[str, Any],
        model_name: str
    ) -> Optional[ProcessedRFP]:
        """
        Process a single RFP opportunity using Kamiwaza model
        This replaces the OpenAI-based assessment
        """
        start_time = time.time()

        try:
            # Convert to RFPOpportunity model
            rfp_opp = RFPOpportunity(
                notice_id=opportunity.get('noticeId', ''),
                solicitation_number=opportunity.get('solicitationNumber'),
                title=opportunity.get('title', 'Unknown'),
                agency=opportunity.get('fullParentPathName', 'Unknown'),
                description=opportunity.get('description', '')[:10000],  # Limit description length
                posted_date=self._parse_date(opportunity.get('postedDate')),
                response_deadline=self._parse_date(opportunity.get('responseDeadLine')),
                naics_code=opportunity.get('naicsCode'),
                set_aside=opportunity.get('typeOfSetAsideDescription'),
                place_of_performance=opportunity.get('placeOfPerformanceCity'),
                url=opportunity.get('uiLink', '')
            )

            # Two-phase assessment using Kamiwaza model
            # Phase 1: Deep analysis
            analysis = self._deep_analysis_phase(rfp_opp, model_name)

            # Phase 2: Extract structured assessment
            assessment = self._extract_assessment(analysis, rfp_opp, model_name)

            assessment.processing_time_ms = int((time.time() - start_time) * 1000)
            assessment.model_used = model_name

            return ProcessedRFP(
                opportunity=rfp_opp,
                assessment=assessment
            )

        except Exception as e:
            logger.error(f"Error processing opportunity {opportunity.get('noticeId')}: {e}")
            return None

    def _deep_analysis_phase(self, opp: RFPOpportunity, model_name: str) -> str:
        """
        Phase 1: Deep analysis using Kamiwaza model
        Replaces OpenAI GPT-5 analysis
        """
        prompt = f"""Analyze this RFP opportunity for potential fit with our company.

COMPANY PROFILE:
{self.company_profile}

PAST WINNING RFPs:
{self.past_rfps[:2000]}  # Include some context from past wins

RFP DETAILS:
Title: {opp.title}
Agency: {opp.agency}
Posted: {opp.posted_date}
Deadline: {opp.response_deadline}
NAICS: {opp.naics_code}
Set-Aside: {opp.set_aside}

FULL DESCRIPTION:
{opp.description}

Please provide a comprehensive analysis including:
1. Relevance score (1-10) based on company fit
2. Explanation of why this is or isn't a good fit
3. Key technical requirements
4. How our company's AI/ML capabilities apply
5. Suggested approach if we pursue
6. Any risks or uncertainties
7. Similar past RFPs we've won (if any)

Focus on AI, machine learning, data analytics, and software development aspects."""

        try:
            # Use synchronous call since we're in a thread
            openai_client = self.kamiwaza_service.get_openai_client(model_name)

            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert RFP analyst specializing in AI/ML opportunities. Provide thorough, actionable analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,  # Kamiwaza models might have different limits
                temperature=0.3  # Lower temperature for consistent analysis
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Kamiwaza model call failed in analysis phase: {e}")
            return f"Analysis failed: {str(e)}"

    def _extract_assessment(
        self,
        analysis: str,
        opp: RFPOpportunity,
        model_name: str
    ) -> RFPAssessment:
        """
        Phase 2: Extract structured assessment from analysis
        Uses Kamiwaza model with structured output
        """
        if not analysis or "failed" in analysis.lower():
            # Return default low-score assessment if analysis failed
            return self._default_assessment(opp)

        # Try to extract structured data using regex patterns first
        score = self._extract_score(analysis)

        # Use Kamiwaza model for structured extraction
        extraction_prompt = f"""Based on this analysis, extract structured information:

{analysis[:3000]}

Provide a JSON response with these exact fields:
{{
    "is_qualified": true/false (true if score >= 7),
    "relevance_score": {score},
    "justification": "one paragraph explaining fit",
    "key_requirements": ["requirement 1", "requirement 2", ...],
    "company_advantages": ["advantage 1", "advantage 2", ...],
    "suggested_approach": "how to approach this RFP",
    "ai_application": "how AI/ML applies to this opportunity",
    "uncertainty_factors": ["risk 1", "risk 2", ...],
    "similar_past_rfps": ["past RFP 1", ...]
}}

Output ONLY valid JSON, no other text."""

        try:
            openai_client = self.kamiwaza_service.get_openai_client(model_name)

            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract structured JSON data from the analysis. Output only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.1  # Very low temperature for consistent JSON
            )

            content = response.choices[0].message.content or "{}"

            # Clean and parse JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                content = json_match.group()

            data = json.loads(content)

            return RFPAssessment(
                is_qualified=data.get('is_qualified', score >= 7),
                qualification_level=QualificationLevel.QUALIFIED if score >= 7 else
                    QualificationLevel.MAYBE if score >= 4 else QualificationLevel.REJECTED,
                relevance_score=data.get('relevance_score', score),
                justification=data.get('justification', 'Analysis completed'),
                key_requirements=data.get('key_requirements', []),
                company_advantages=data.get('company_advantages', []),
                suggested_approach=data.get('suggested_approach', 'Review RFP details'),
                ai_application=data.get('ai_application', 'AI/ML capabilities applicable'),
                uncertainty_factors=data.get('uncertainty_factors'),
                similar_past_rfps=data.get('similar_past_rfps'),
                model_used=model_name,
                processing_time_ms=0  # Will be set by caller
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON extraction failed: {e}")
            return self._assessment_from_analysis(analysis, score, opp)
        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")
            return self._assessment_from_analysis(analysis, score, opp)

    def _extract_score(self, analysis: str) -> float:
        """Extract numeric score from analysis text"""
        # Look for patterns like "score: 8/10" or "rating: 7" or just "8/10"
        patterns = [
            r'(?:score|rating)[:\s]*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:/|out of)\s*10',
            r'(?:give|rate|score)[^\d]*(\d+(?:\.\d+)?)'
        ]

        for pattern in patterns:
            match = re.search(pattern, analysis.lower())
            if match:
                score = float(match.group(1))
                if score <= 10:
                    return score

        return 0.0

    def _assessment_from_analysis(
        self,
        analysis: str,
        score: float,
        opp: RFPOpportunity
    ) -> RFPAssessment:
        """Create assessment from raw analysis when JSON extraction fails"""
        # Look for key phrases to determine qualification
        qualified_keywords = ['qualified', 'strong fit', 'excellent match', 'pursue', 'recommend']
        is_qualified = (
            score >= 7 or
            any(keyword in analysis.lower() for keyword in qualified_keywords)
        )

        # Extract first few sentences as justification
        sentences = analysis.split('.')[:3]
        justification = '. '.join(sentences).strip()[:500]

        return RFPAssessment(
            is_qualified=is_qualified,
            qualification_level=QualificationLevel.QUALIFIED if score >= 7 else
                QualificationLevel.MAYBE if score >= 4 else QualificationLevel.REJECTED,
            relevance_score=score,
            justification=justification or "Analysis completed",
            key_requirements=["See full analysis for requirements"],
            company_advantages=["See full analysis for advantages"],
            suggested_approach="Review full RFP documentation",
            ai_application="AI/ML capabilities may be applicable",
            uncertainty_factors=["Manual review recommended"],
            model_used="unknown",
            processing_time_ms=0
        )

    def _default_assessment(self, opp: RFPOpportunity) -> RFPAssessment:
        """Default assessment when processing fails"""
        return RFPAssessment(
            is_qualified=False,
            qualification_level=QualificationLevel.REJECTED,
            relevance_score=0,
            justification="Processing failed - manual review required",
            key_requirements=[],
            company_advantages=[],
            suggested_approach="Manual review required",
            ai_application="Unable to assess",
            uncertainty_factors=["Processing error"],
            model_used="none",
            processing_time_ms=0
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None

        try:
            # Try common date formats
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%m/%d/%Y',
                '%m-%d-%Y'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            # If no format matches, try to parse the date part
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
                return datetime.strptime(date_str, '%Y-%m-%d')

        except Exception as e:
            logger.debug(f"Could not parse date '{date_str}': {e}")

        return None