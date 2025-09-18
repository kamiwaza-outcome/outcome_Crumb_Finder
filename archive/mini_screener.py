"""
GPT-5-mini Initial Screener
Fast, lightweight first-pass evaluation using GPT-5-mini
"""

import openai
import json
import logging
import os
import time
import random
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class MiniScreener:
    def __init__(self, api_key: str):
        """Initialize the mini screener with GPT-5-mini"""
        # Clear any proxy settings
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None) 
        os.environ.pop('https_proxy', None)
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=api_key,
            max_retries=3,
            timeout=120  # 2 minute timeout for comprehensive analysis
        )
        self.model = 'gpt-5-mini'  # Using GPT-5-mini for fast screening
        
    def quick_score(self, opportunity: Dict) -> Dict:
        """
        Quick scoring pass with GPT-5-mini
        Returns score and brief justification only
        """
        
        # Get key information for quick assessment
        title = opportunity.get('title', 'N/A')
        agency = opportunity.get('fullParentPathName', 'N/A')
        naics = opportunity.get('naicsCode', 'N/A')
        psc = opportunity.get('classificationCode', 'N/A')
        
        # Get full description for comprehensive assessment
        description = opportunity.get('description', '')
        
        # Comprehensive prompt for scoring with full context
        prompt = f"""Score this RFP from 1-10 for relevance to AI/data/software companies.

RFP: {title}
Agency: {agency}
NAICS: {naics}
PSC: {psc}
Full Description: {description}

Scoring Guide:
1-3: Not relevant (construction, maintenance, non-IT services)
4-6: Possibly relevant (has IT/data components but unclear AI fit)
7-10: Highly relevant (AI, ML, data processing, software development)

Respond with JSON only:
{{
    "score": 1-10,
    "reason": "One sentence explanation"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a rapid RFP screener. Respond only with JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=32000,  # NEW: 32k tokens for comprehensive mini analysis
                response_format={"type": "json_object"},
                timeout=60  # 60 second timeout
            )
            
            content = response.choices[0].message.content
            
            if not content:
                logger.error(f"Empty response from GPT-5-mini for {opportunity.get('noticeId')}")
                return {"score": 0, "reason": "Empty response from model"}
            
            result = json.loads(content)
            
            # Ensure score is in valid range
            score = max(1, min(10, result.get('score', 0)))
            
            logger.info(f"Mini-screened {opportunity.get('noticeId')}: Score {score}")
            
            return {
                "score": score,
                "reason": result.get('reason', 'No reason provided'),
                "screener": "gpt-5-mini"
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in mini screener: {str(e)}")
            return {"score": 0, "reason": f"JSON error: {str(e)}", "screener": "gpt-5-mini"}
        except Exception as e:
            logger.error(f"Error in mini screener: {str(e)}")
            return {"score": 0, "reason": f"Error: {str(e)}", "screener": "gpt-5-mini"}
    
    def batch_screen(self, opportunities: List[Dict], threshold: int = 4) -> Tuple[List[Dict], List[Dict]]:
        """
        Screen a batch of opportunities
        Returns (opportunities_for_deep_analysis, rejected_opportunities)
        """
        
        for_deep_analysis = []
        rejected = []
        
        for opp in opportunities:
            result = self.quick_score(opp)
            
            # Add screening result to opportunity
            opp['mini_screen'] = result
            
            if result['score'] >= threshold:
                for_deep_analysis.append(opp)
                logger.info(f"Passed to deep analysis: {opp.get('title', 'Unknown')[:50]} (score: {result['score']})")
            else:
                rejected.append(opp)
                logger.debug(f"Rejected by mini screener: {opp.get('title', 'Unknown')[:50]} (score: {result['score']})")
            
            # Small delay to avoid rate limits
            time.sleep(0.1)
        
        logger.info(f"Mini screening complete: {len(for_deep_analysis)} for deep analysis, {len(rejected)} rejected")
        
        return for_deep_analysis, rejected