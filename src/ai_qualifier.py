import openai
import json
import logging
import os
import re
import time
import random
from typing import Dict, Any, Optional
from datetime import datetime
from config import Config
from src.sanitizer import Sanitizer

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker to handle repeated failures"""
    def __init__(self, failure_threshold=None, recovery_timeout=None):
        self.failure_count = 0
        self.consecutive_failures = 0
        self.failure_threshold = failure_threshold or Config.CIRCUIT_BREAKER_THRESHOLD
        self.recovery_timeout = recovery_timeout or Config.CIRCUIT_BREAKER_TIMEOUT
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.failure_types = {}  # Track different types of failures
    
    def call(self, func):
        if self.state == "open":
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is open - service unavailable")
        
        try:
            result = func()
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                self.consecutive_failures = 0
                logger.info("Circuit breaker closed - service recovered")
            else:
                self.consecutive_failures = 0  # Reset on success
            return result
        except Exception as e:
            self.consecutive_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Track failure types
            error_type = type(e).__name__
            self.failure_types[error_type] = self.failure_types.get(error_type, 0) + 1
            
            if self.consecutive_failures >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.consecutive_failures} consecutive failures. Errors: {self.failure_types}")
            raise

class AIQualifier:
    def __init__(self, api_key: str):
        # Initialize OpenAI client - avoid proxy issues in GitHub Actions
        # Clear any HTTP proxy settings that might interfere
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None) 
        os.environ.pop('https_proxy', None)
        
        # Initialize with retry configuration
        self.client = openai.OpenAI(
            api_key=api_key,
            max_retries=5,  # Automatic retries for transient errors
            timeout=90  # 90 second default timeout
        )
        self.model = Config.GPT_MODEL  # Using GPT-5 from config
        
        # Circuit breaker for handling repeated failures
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Load past winning RFPs if available
        self.past_rfps = self._load_past_rfps()
    
    def _load_past_rfps(self) -> str:
        """Load past winning RFPs from file"""
        try:
            # Look for winning_rfps.txt in the data directory
            rfp_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'winning_rfps.txt')
            if os.path.exists(rfp_file):
                with open(rfp_file, 'r') as f:
                    return f.read()
            else:
                logger.warning("winning_rfps.txt not found, using only company profile")
                return ""
        except Exception as e:
            logger.error(f"Error loading past RFPs: {str(e)}")
            return ""
    
    def assess_opportunity(self, opportunity: Dict, company_profile: str = None) -> Dict:
        """Two-phase assessment: Full reasoning then JSON extraction"""
        
        if company_profile is None:
            company_profile = Config.get_company_info()
        
        # Temporarily disable two-phase for GPT-5 due to timeout issues
        # Will use single-phase with higher token limit instead
        if False and 'gpt-5' in self.model.lower():
            try:
                # Phase 1: Deep Analysis (Let GPT-5 think freely)
                analysis = self._deep_analysis_phase(opportunity, company_profile)
                
                if not analysis:
                    logger.error("Phase 1 failed - falling back to single-phase")
                    return self._single_phase_assessment(opportunity, company_profile)
                
                # Phase 2: Structured Extraction (Convert to clean JSON)
                result = self._json_extraction_phase(analysis, opportunity)
                
                if not result:
                    logger.error("Phase 2 failed - attempting fallback extraction")
                    # Fallback: Try to extract key info manually
                    result = self._fallback_extraction(analysis, opportunity)
                
                return result
            except Exception as e:
                logger.error(f"Two-phase failed: {str(e)}, falling back to single-phase")
                return self._single_phase_assessment(opportunity, company_profile)
        
        # Original single-phase approach for GPT-4 and other models
        return self._single_phase_assessment(opportunity, company_profile)
    
    def _single_phase_assessment(self, opportunity: Dict, company_profile: str) -> Dict:
        """Original single-phase assessment for GPT-4 models"""
        
        if company_profile is None:
            company_profile = Config.get_company_info()
        
        # Get FULL description, not truncated
        # Get FULL description - NO TRUNCATION
        # Money and time are not constraints - let GPT see everything
        full_description = opportunity.get('description', 'N/A')
        
        prompt = f"""
        You are an expert RFP analyst evaluating opportunities for {Config.get_company_name()}.

        COMPANY PROFILE:
        {company_profile}
        
        PAST WINNING RFPs (Examples of what {Config.get_company_name()} has successfully bid on):
        {self.past_rfps if self.past_rfps else "No past RFP examples available"}
        
        NEW OPPORTUNITY TO EVALUATE:
        Title: {opportunity.get('title', 'N/A')}
        Agency: {opportunity.get('fullParentPathName', 'N/A')}
        Type: {opportunity.get('type', 'N/A')}
        NAICS Code: {opportunity.get('naicsCode', 'N/A')}
        PSC Code: {opportunity.get('classificationCode', 'N/A')}
        Response Deadline: {opportunity.get('responseDeadLine', 'N/A')}
        Award Amount: {opportunity.get('awardAmount', 'Not specified')}
        
        FULL DESCRIPTION:
        {full_description}
        
        EVALUATION APPROACH:
        1. Compare this opportunity to the past winning RFPs - does it have similar characteristics?
        2. Does it involve any of these areas where {Config.get_company_name()} excels:
           {chr(10).join(f'   - {capability}' for capability in Config.get_company_capabilities())}
        3. Could {Config.get_company_name()}'s solutions solve the core problem?
        4. Is this the type of work {Config.get_company_name()} has won before?
        
        IMPORTANT SCORING GUIDELINES:
        - Score 1-3: Clearly not relevant (construction, pure hardware, no data/software component)
        - Score 4-6: Potentially relevant but unclear (has data/IT elements but uncertain fit)
        - Score 7-10: Strong fit with {Config.get_company_name()}'s capabilities
        
        Consider these factors:
        - Does it involve data processing, analytics, or automation?
        - Could technology solutions improve the outcome?
        - Is there a software/IT component?
        - Does it match patterns from past wins?
        
        Respond with JSON only:
        {{
            "is_qualified": true/false (true if score >= 7),
            "relevance_score": 1-10,
            "justification": "Detailed explanation of score and fit assessment",
            "key_requirements": ["req1", "req2", "req3"],
            "company_advantages": ["advantage1", "advantage2"],
            "suggested_approach": "High-level approach based on similar past projects",
            "ai_application": "Specific ways {Config.get_company_name()}'s solutions would address this",
            "similar_past_rfps": ["List any similar past RFPs from the examples"],
            "uncertainty_factors": ["For 4-6 scores, what makes this uncertain"]
        }}
        """
        
        try:
            # GPT-5 requires max_completion_tokens instead of max_tokens
            # Auto-detect which parameter to use based on model
            if 'gpt-5' in self.model.lower():
                # GPT-5 with robust error handling
                response = self._call_gpt5_with_retry(prompt, opportunity)
            else:
                # GPT-4 and earlier models use max_tokens
                response = self._retry_with_backoff(
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are an expert RFP analyst. Respond only with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=2000,  # GPT-4 and earlier parameter
                        timeout=60  # 1 minute timeout for GPT-4
                    ),
                    max_retries=3
                )
            
            # Clean the response in case there's extra text
            content = response.choices[0].message.content
            
            # Handle empty responses
            if not content:
                logger.error("Empty response from GPT model")
                return self._default_response("Empty response from model")
            
            # Extract JSON if it's wrapped in other text
            if '{' in content and '}' in content:
                json_start = content.index('{')
                json_end = content.rindex('}') + 1
                content = content[json_start:json_end]
            
            result = json.loads(content)
            
            # Apply threshold from config
            threshold = 6
            if result.get('relevance_score', 0) < threshold:
                result['is_qualified'] = False
            
            logger.info(f"Assessed {opportunity.get('noticeId')}: Score {result['relevance_score']}, Qualified: {result['is_qualified']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return self._default_response(f"JSON parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error assessing opportunity: {str(e)}")
            # Try fallback to GPT-4o if available
            if 'gpt-5' in self.model.lower() and '502' not in str(e):
                logger.info("Attempting fallback to GPT-4o")
                return self._fallback_to_gpt4(opportunity, company_profile)
            return self._default_response(f"Assessment error: {str(e)}")
    
    def _calculate_optimal_tokens(self, opportunity: Dict) -> int:
        """Calculate optimal token allocation based on RFP complexity"""
        desc_len = len(opportunity.get('description', ''))
        
        # GPT-5 needs more tokens for complex RFPs
        if desc_len < 1000:
            return 8000  # Simple RFP
        elif desc_len < 5000:
            return 12000  # Medium complexity
        else:
            return 15000  # Complex RFP
    
    def _retry_with_backoff(self, func, max_retries=5):
        """Retry with exponential backoff and jitter"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                error_str = str(e)
                if "502" in error_str or "503" in error_str or "504" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Gateway error on attempt {attempt + 1}, retrying in {wait_time:.1f}s")
                        time.sleep(wait_time)
                        continue
                raise
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    def _call_gpt5_with_retry(self, prompt: str, opportunity: Dict):
        """Robust GPT-5 call with multiple fallback strategies"""
        
        # Calculate optimal tokens based on complexity
        tokens = self._calculate_optimal_tokens(opportunity)
        
        def make_request_with_format():
            """Try with forced JSON format first"""
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert RFP analyst. You must respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=50000,  # Maximum tokens for comprehensive analysis
                response_format={"type": "json_object"},  # Force JSON output
                timeout=300  # 5 minute timeout for GPT-5
            )
        
        def make_request_without_format():
            """Fallback without forced format if that fails"""
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert RFP analyst. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=50000,  # Maximum tokens even for fallback
                timeout=300  # 5 minute timeout
            )
        
        try:
            # Try with circuit breaker
            response = self.circuit_breaker.call(
                lambda: self._retry_with_backoff(make_request_with_format, max_retries=3)
            )
            
            # Check for empty response
            if not response.choices[0].message.content:
                logger.warning("Empty response from GPT-5, retrying with more tokens")
                response = self._retry_with_backoff(make_request_without_format, max_retries=2)
            
            return response
            
        except Exception as e:
            logger.error(f"GPT-5 call failed after all retries: {str(e)}")
            raise
    
    def _fallback_to_gpt4(self, opportunity: Dict, company_profile: str) -> Dict:
        """Fallback to GPT-4o when GPT-5 fails"""
        try:
            # Temporarily switch model
            original_model = self.model
            self.model = 'gpt-4o'
            
            # Use single-phase with GPT-4o
            result = self._single_phase_assessment(opportunity, company_profile)
            
            # Restore original model
            self.model = original_model
            
            # Add flag to indicate fallback was used
            result['fallback_model'] = 'gpt-4o'
            
            return result
        except Exception as e:
            logger.error(f"GPT-4o fallback also failed: {str(e)}")
            return self._default_response(f"Both GPT-5 and GPT-4o failed: {str(e)}")
    
    def _deep_analysis_phase(self, opportunity: Dict, company_profile: str) -> str:
        """Phase 1: Let GPT-5 do comprehensive analysis without JSON constraints"""
        
        # Get FULL description - NO TRUNCATION
        # Money and time are not constraints - let GPT see everything
        full_description = opportunity.get('description', 'N/A')
        
        # Simplified prompt for GPT-5 to avoid empty responses
        analysis_prompt = f"""Analyze this RFP for {Config.get_company_name()}.

{Config.get_company_name()} capabilities: {Config.get_company_info()}

RFP: {opportunity.get('title', 'N/A')}
Agency: {opportunity.get('fullParentPathName', 'N/A')}
NAICS: {opportunity.get('naicsCode', 'N/A')}

Description: {full_description}

Provide:
1. Score (1-10)
2. How {Config.get_company_name()} fits
3. Key requirements
4. Suggested approach
5. Risks/uncertainties"""
        
        try:
            # Give GPT-5 plenty of room to think (but not too much to avoid timeouts)
            logger.info(f"Phase 1: Calling {self.model} with max_completion_tokens=100000")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert RFP analyst. Provide thorough, detailed analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_completion_tokens=100000,  # NEW: 100k tokens for ultra-deep analysis
                timeout=300  # 5 minute timeout for complex analysis
            )
            
            analysis = response.choices[0].message.content
            
            if not analysis:
                logger.error("Empty analysis from Phase 1")
                return None
                
            logger.info(f"Phase 1 complete: {len(analysis)} chars of analysis generated")
            return analysis
            
        except Exception as e:
            logger.error(f"Phase 1 error: {str(e)}")
            return None
    
    def _json_extraction_phase(self, analysis: str, opportunity: Dict) -> Dict:
        """Phase 2: Extract structured JSON from the analysis"""
        
        # Simpler extraction prompt for GPT-5
        extraction_prompt = f"""Extract JSON from this analysis:

{analysis[:4000]}

Output JSON:
{{
    "is_qualified": boolean,
    "relevance_score": number 1-10,
    "justification": "reason",
    "key_requirements": ["req1", "req2"],
    "company_advantages": ["adv1", "adv2"],
    "suggested_approach": "approach",
    "ai_application": "how {Config.get_company_name()} would help",
    "similar_past_rfps": [],
    "uncertainty_factors": ["risk1"]
}}"""
        
        try:
            logger.info(f"Phase 2: Extracting JSON with {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract and return ONLY valid JSON."},
                    {"role": "user", "content": extraction_prompt}
                ],
                max_completion_tokens=10000,  # Give plenty of room for detailed output
                timeout=60  # 60 second timeout for extraction
            )
            
            content = response.choices[0].message.content
            
            if not content:
                logger.error("Empty JSON extraction from Phase 2")
                return None
            
            # Clean and parse JSON
            if '{' in content and '}' in content:
                json_start = content.index('{')
                json_end = content.rindex('}') + 1
                content = content[json_start:json_end]
            
            result = json.loads(content)
            
            # Apply threshold
            threshold = 6
            if result.get('relevance_score', 0) < threshold:
                result['is_qualified'] = False
            
            logger.info(f"Phase 2 complete: Score {result.get('relevance_score')}, Qualified: {result.get('is_qualified')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in Phase 2: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Phase 2 error: {str(e)}")
            return None
    
    def _fallback_extraction(self, analysis: str, opportunity: Dict) -> Dict:
        """Fallback: Extract key information using regex/heuristics"""
        
        # Try to extract score using regex
        score_match = re.search(r'(?:score|rating).*?(\d+)(?:\s*(?:/|out of)\s*10)?', analysis.lower())
        score = int(score_match.group(1)) if score_match else 0
        
        # Look for qualification keywords
        qualified_keywords = ['qualified', 'strong fit', 'excellent match', 'highly relevant']
        is_qualified = any(keyword in analysis.lower() for keyword in qualified_keywords) or score >= 7
        
        # Extract first substantive sentence as justification
        sentences = analysis.split('.')[:3]
        justification = '. '.join(sentences).strip()[:500]
        
        logger.warning(f"Using fallback extraction - Score: {score}")
        
        return {
            "is_qualified": is_qualified,
            "relevance_score": score,
            "justification": justification or "Analysis completed but structured extraction failed",
            "key_requirements": ["See full analysis for details"],
            "company_advantages": ["See full analysis for details"],
            "suggested_approach": "Review full analysis for approach",
            "ai_application": "Review full analysis for details",
            "similar_past_rfps": [],
            "uncertainty_factors": ["Structured extraction failed - manual review recommended"]
        }
    
    def _default_response(self, error_msg: str) -> Dict:
        """Enhanced default response with error tracking"""
        
        # Log to separate error file for analysis
        with open('gpt5_errors.log', 'a') as f:
            f.write(f"{datetime.now()}: {error_msg}\n")
        
        return {
            "is_qualified": False,
            "relevance_score": 0,
            "justification": error_msg,
            "key_requirements": [],
            "company_advantages": [],
            "suggested_approach": "",
            "ai_application": "",
            "error": True,  # Flag for retry logic
            "error_type": "empty_response" if "empty" in error_msg.lower() else "other"
        }
    
    def generate_summary(self, opportunity: Dict, assessment: Dict) -> str:
        """Generate a brief summary for Slack notification"""
        summary = f"*{opportunity.get('title', 'Unknown')}*\n"
        summary += f"Agency: {opportunity.get('fullParentPathName', 'Unknown')}\n"
        summary += f"Relevance Score: {assessment.get('relevance_score', 0)}/10\n"
        summary += f"Deadline: {opportunity.get('responseDeadLine', 'Not specified')}\n"
        summary += f"Justification: {assessment.get('justification', 'N/A')}\n"
        summary += f"Application: {assessment.get('ai_application', 'N/A')}"
        
        return summary