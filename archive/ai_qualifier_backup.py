import openai
import json
import logging
import os
from typing import Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class AIQualifier:
    def __init__(self, api_key: str):
        # Initialize OpenAI client - avoid proxy issues in GitHub Actions
        # Clear any HTTP proxy settings that might interfere
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None) 
        os.environ.pop('https_proxy', None)
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = Config.GPT_MODEL  # Using GPT-5 from config
        
        # Load past winning RFPs if available
        self.past_rfps = self._load_past_rfps()
    
    def _load_past_rfps(self) -> str:
        """Load past winning RFPs from file"""
        try:
            rfp_file = os.path.join(os.path.dirname(__file__), 'winning_rfps.txt')
            if os.path.exists(rfp_file):
                with open(rfp_file, 'r') as f:
                    return f.read()
            else:
                logger.warning("winning_rfps.txt not found, using only company profile")
                return ""
        except Exception as e:
            logger.error(f"Error loading past RFPs: {str(e)}")
            return ""
    
    def assess_opportunity(self, opportunity: Dict, kamiwaza_profile: str = None) -> Dict:
        """Assess if opportunity is relevant for Kamiwaza"""
        
        if kamiwaza_profile is None:
            kamiwaza_profile = Config.KAMIWAZA_INFO
        
        # Get FULL description, not truncated
        full_description = opportunity.get('description', 'N/A')
        if len(full_description) > 10000:
            full_description = full_description[:10000] + "... [truncated]"
        
        prompt = f"""
        You are an expert RFP analyst evaluating opportunities for Kamiwaza.
        
        KAMIWAZA COMPANY PROFILE:
        {kamiwaza_profile}
        
        PAST WINNING RFPs (Examples of what Kamiwaza has successfully bid on):
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
        2. Does it involve any of these areas where Kamiwaza excels:
           - Large-scale data processing and analysis
           - AI/ML automation of manual processes  
           - Legacy system modernization
           - Data quality improvement
           - Predictive analytics
           - Document processing
           - Multi-modal data fusion
           - Distributed/edge computing
           - AI orchestration and LLM orchestration
           - Inference mesh and distributed inference
           - Agentic AI and autonomous agents
           - Private/on-prem AI deployment
           - Hybrid cloud AI solutions
           - Data pipeline automation
           - Vector databases and embeddings
           - Edge inference capabilities
           - Model Context Protocol (MCP) implementations
           - Enterprise AI platforms
           - Data governance with AI
        3. Could Kamiwaza's AI orchestration platform solve the core problem?
        4. Is this the type of work Kamiwaza has won before?
        
        IMPORTANT SCORING GUIDELINES:
        - Score 1-3: Clearly not relevant (construction, pure hardware, no data/software component)
        - Score 4-6: Potentially relevant but unclear (has data/IT elements but uncertain AI fit)
        - Score 7-10: Strong fit with Kamiwaza's capabilities
        
        Consider these factors:
        - Does it involve data processing, analytics, or automation?
        - Could AI/ML improve the solution?
        - Is there a software/IT component?
        - Does it match patterns from past wins?
        
        Respond with JSON only:
        {{
            "is_qualified": true/false (true if score >= 7),
            "relevance_score": 1-10,
            "justification": "Detailed explanation of score and fit assessment",
            "key_requirements": ["req1", "req2", "req3"],
            "kamiwaza_advantages": ["advantage1", "advantage2"],
            "suggested_approach": "High-level approach based on similar past projects",
            "ai_application": "Specific ways Kamiwaza's platform would solve this",
            "similar_past_rfps": ["List any similar past RFPs from the examples"],
            "uncertainty_factors": ["For 4-6 scores, what makes this uncertain"]
        }}
        """
        
        try:
            # GPT-5 requires max_completion_tokens instead of max_tokens
            # Auto-detect which parameter to use based on model
            if 'gpt-5' in self.model.lower():
                # GPT-5 models use max_completion_tokens and only support temperature=1
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert RFP analyst. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    # temperature parameter not supported in GPT-5, uses default of 1
                    max_completion_tokens=2000  # GPT-5 parameter (up to 128,000 supported)
                )
            else:
                # GPT-4 and earlier models use max_tokens
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert RFP analyst. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000  # GPT-4 and earlier parameter
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
            return self._default_response(f"Assessment error: {str(e)}")
    
    def _default_response(self, error_msg: str) -> Dict:
        """Return default response in case of errors"""
        return {
            "is_qualified": False,
            "relevance_score": 0,
            "justification": error_msg,
            "key_requirements": [],
            "kamiwaza_advantages": [],
            "suggested_approach": "",
            "ai_application": ""
        }
    
    def generate_summary(self, opportunity: Dict, assessment: Dict) -> str:
        """Generate a brief summary for Slack notification"""
        summary = f"*{opportunity.get('title', 'Unknown')}*\n"
        summary += f"Agency: {opportunity.get('fullParentPathName', 'Unknown')}\n"
        summary += f"AI Score: {assessment.get('relevance_score', 0)}/10\n"
        summary += f"Deadline: {opportunity.get('responseDeadLine', 'Not specified')}\n"
        summary += f"Justification: {assessment.get('justification', 'N/A')}\n"
        summary += f"AI Application: {assessment.get('ai_application', 'N/A')}"
        
        return summary