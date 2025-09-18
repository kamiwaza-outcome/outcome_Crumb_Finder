import requests
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    def send_opportunity_notification(self, opportunity: Dict, assessment: Dict, folder_url: str, sheet_url: str):
        """Send notification for a single qualified opportunity"""
        
        # Create rich Slack message with blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎯 New RFP Opportunity Found",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{opportunity.get('title', 'N/A')[:100]}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Agency:*\n{opportunity.get('fullParentPathName', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Relevance Score:*\n{assessment.get('relevance_score', 0)}/10"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Response Deadline:*\n{opportunity.get('responseDeadLine', 'Not specified')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Notice ID:*\n{opportunity.get('noticeId', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Posted Date:*\n{opportunity.get('postedDate', 'N/A')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Assessment:*\n{assessment.get('justification', 'No justification provided')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Solution Application:*\n{assessment.get('ai_application', 'Not specified')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key Requirements:*\n• " + "\n• ".join(assessment.get('key_requirements', ['None identified']))
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Suggested Approach:*\n{assessment.get('suggested_approach', 'No approach suggested')}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View on SAM.gov",
                            "emoji": True
                        },
                        "url": opportunity.get('uiLink', '#'),
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Open Drive Folder",
                            "emoji": True
                        },
                        "url": folder_url
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Tracking Sheet",
                            "emoji": True
                        },
                        "url": sheet_url
                    }
                ]
            }
        ]
        
        message = {
            "blocks": blocks,
            "text": f"New RFP: {opportunity.get('title', 'Unknown')}"  # Fallback text
        }
        
        try:
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
            logger.info(f"Sent Slack notification for {opportunity.get('noticeId')}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
    
    def send_raw_message(self, message: Dict) -> bool:
        """Send a raw message with custom blocks to Slack"""
        try:
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
            logger.info("Sent custom Slack message successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack message: {str(e)}")
            return False
    
    def send_daily_summary(self, total_found: int, qualified: int, opportunities: List[Dict]):
        """Send daily summary of all discovered opportunities"""
        
        current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Daily RFP Discovery Summary",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Discovery completed on {current_time}*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Opportunities Found:*\n{total_found}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Qualified for {Config.get_company_name()}:*\n{qualified}"
                    }
                ]
            }
        ]
        
        if opportunities:
            # Add top opportunities
            opp_text = "*Top Qualified Opportunities:*\n"
            for i, item in enumerate(opportunities[:5], 1):
                opp = item['opportunity']
                assessment = item['assessment']
                opp_text += f"{i}. *{opp.get('title', 'Unknown')[:50]}...* (Score: {assessment.get('relevance_score', 0)}/10)\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": opp_text
                }
            })
        else:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_No qualified opportunities found today._"
                }
            })
        
        message = {
            "blocks": blocks,
            "text": f"Daily Summary: {qualified} qualified RFPs found"
        }
        
        try:
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
            logger.info("Sent daily summary to Slack")
        except Exception as e:
            logger.error(f"Failed to send daily summary: {str(e)}")
    
    def send_error_notification(self, error_message: str):
        """Send error notification to Slack"""
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ RFP Discovery Error",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"An error occurred during RFP discovery:\n```{error_message}```"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]
        
        message = {
            "blocks": blocks,
            "text": f"Error: {error_message[:100]}"
        }
        
        try:
            response = requests.post(self.webhook_url, json=message)
            response.raise_for_status()
            logger.info("Sent error notification to Slack")
        except Exception as e:
            logger.error(f"Failed to send error notification: {str(e)}")