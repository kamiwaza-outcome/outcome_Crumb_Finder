#!/usr/bin/env python3
"""
Weekly RFP Obituary Generator
Memorializes expired high-value RFPs with humor and education
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from src.slack_notifier import SlackNotifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RFPObituary:
    """Creates memorable obituaries for expired RFPs"""
    
    def __init__(self):
        """Initialize Google Sheets and OpenAI"""
        try:
            # Google Sheets
            self.credentials = service_account.Credentials.from_service_account_file(
                Config.GOOGLE_SHEETS_CREDS_PATH,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            
            # OpenAI
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
            
            # Slack - use obituary-specific webhook for the obituary channel
            webhook_url = Config.SLACK_OBITUARY_WEBHOOK_URL if hasattr(Config, 'SLACK_OBITUARY_WEBHOOK_URL') and Config.SLACK_OBITUARY_WEBHOOK_URL else Config.SLACK_WEBHOOK_URL
            self.slack = SlackNotifier(webhook_url)
            
        except Exception as e:
            logger.error(f"Failed to initialize: {str(e)}")
            raise
    
    def get_expired_rfps(self, days_back: int = 7) -> List[Dict]:
        """Get RFPs that expired in the last N days"""
        try:
            # Get all data from main sheet
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=Config.SPREADSHEET_ID,
                range='Sheet1!A:S'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return []
            
            headers = values[0]
            col_indices = {header: i for i, header in enumerate(headers)}
            
            expired_rfps = []
            today = datetime.now().date()
            week_ago = today - timedelta(days=days_back)
            
            for row in values[1:]:
                if len(row) <= max(col_indices.values()):
                    continue
                
                # Check if status is Expired and score is 7+
                status = row[col_indices.get('Status', 2)] if 'Status' in col_indices else ''
                score_text = row[col_indices.get('AI Score', 13)] if 'AI Score' in col_indices else '0'
                
                # Parse score (handles both "8/10 - High" and "High" formats)
                score = 0
                if 'Medium' in str(score_text) or '7/10' in str(score_text) or score_text == '7':
                    score = 7
                elif 'High' in str(score_text) or '8/10' in str(score_text) or score_text == '8':
                    score = 8
                elif 'Excellent' in str(score_text) or '9/10' in str(score_text) or score_text == '9':
                    score = 9
                elif 'Perfect' in str(score_text) or '10/10' in str(score_text) or score_text == '10':
                    score = 10
                else:
                    try:
                        score = int(float(score_text))
                    except:
                        score = 0
                
                if status == 'Expired' and score >= 7:
                    # Check if expired this week
                    deadline = row[col_indices.get('Response Deadline', 3)] if 'Response Deadline' in col_indices else ''
                    
                    if deadline:
                        try:
                            if 'T' in deadline:
                                deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00')).date()
                            else:
                                deadline_date = datetime.strptime(deadline[:10], '%Y-%m-%d').date()
                            
                            # If expired within our window
                            if week_ago <= deadline_date <= today:
                                rfp = {
                                    'title': row[col_indices.get('Title', 6)][:100] if 'Title' in col_indices else 'Unknown',
                                    'agency': row[col_indices.get('Agency', 7)] if 'Agency' in col_indices else 'Unknown',
                                    'score': score,
                                    'score_text': score_text,
                                    'deadline': deadline_date.strftime('%Y-%m-%d'),
                                    'posted_date': row[col_indices.get('Posted Date', 10)] if 'Posted Date' in col_indices else '',
                                    'naics': row[col_indices.get('NAICS', 8)] if 'NAICS' in col_indices else '',
                                    'psc': row[col_indices.get('PSC', 9)] if 'PSC' in col_indices else '',
                                    'link': row[col_indices.get('SAM.gov Link', 11)] if 'SAM.gov Link' in col_indices else '',
                                    'justification': row[col_indices.get('AI Justification', 14)][:200] if 'AI Justification' in col_indices else '',
                                    'notice_id': row[col_indices.get('Notice ID', 4)] if 'Notice ID' in col_indices else ''
                                }
                                
                                # Calculate days it was alive
                                if rfp['posted_date']:
                                    try:
                                        posted = datetime.strptime(rfp['posted_date'][:10], '%Y-%m-%d').date()
                                        rfp['days_alive'] = (deadline_date - posted).days
                                    except:
                                        rfp['days_alive'] = 30  # Default
                                else:
                                    rfp['days_alive'] = 30
                                
                                expired_rfps.append(rfp)
                        except Exception as e:
                            logger.warning(f"Error parsing deadline: {e}")
            
            # Sort by score (highest first)
            expired_rfps.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Found {len(expired_rfps)} expired RFPs from the past {days_back} days")
            return expired_rfps
            
        except Exception as e:
            logger.error(f"Error getting expired RFPs: {str(e)}")
            return []
    
    def get_expiring_soon(self, days_ahead: int = 7) -> List[Dict]:
        """Get RFPs expiring in the next N days"""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=Config.SPREADSHEET_ID,
                range='Sheet1!A:S'
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:
                return []
            
            headers = values[0]
            col_indices = {header: i for i, header in enumerate(headers)}
            
            expiring_rfps = []
            today = datetime.now().date()
            next_week = today + timedelta(days=days_ahead)
            
            for row in values[1:]:
                if len(row) <= max(col_indices.values()):
                    continue
                
                status = row[col_indices.get('Status', 2)] if 'Status' in col_indices else ''
                score_text = row[col_indices.get('AI Score', 13)] if 'AI Score' in col_indices else '0'
                
                # Parse score (handles both "8/10 - High" and "High" formats)
                score = 0
                if 'Medium' in str(score_text) or '7/10' in str(score_text) or score_text == '7':
                    score = 7
                elif 'High' in str(score_text) or '8/10' in str(score_text) or score_text == '8':
                    score = 8
                elif 'Excellent' in str(score_text) or '9/10' in str(score_text) or score_text == '9':
                    score = 9
                elif 'Perfect' in str(score_text) or '10/10' in str(score_text) or score_text == '10':
                    score = 10
                else:
                    try:
                        score = int(float(score_text))
                    except:
                        score = 0
                
                # Check if expiring soon (not already expired) and high score
                if status in ['Active', 'Expiring', 'New'] and score >= 7:
                    deadline = row[col_indices.get('Response Deadline', 3)] if 'Response Deadline' in col_indices else ''
                    
                    if deadline:
                        try:
                            if 'T' in deadline:
                                deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00')).date()
                            else:
                                deadline_date = datetime.strptime(deadline[:10], '%Y-%m-%d').date()
                            
                            # If expiring within our window
                            if today < deadline_date <= next_week:
                                days_left = (deadline_date - today).days
                                
                                rfp = {
                                    'title': row[col_indices.get('Title', 6)][:100] if 'Title' in col_indices else 'Unknown',
                                    'agency': row[col_indices.get('Agency', 7)] if 'Agency' in col_indices else 'Unknown',
                                    'score': score,
                                    'score_text': score_text,
                                    'deadline': deadline_date.strftime('%Y-%m-%d'),
                                    'days_left': days_left,
                                    'naics': row[col_indices.get('NAICS', 8)] if 'NAICS' in col_indices else '',
                                    'link': row[col_indices.get('SAM.gov Link', 11)] if 'SAM.gov Link' in col_indices else ''
                                }
                                
                                expiring_rfps.append(rfp)
                        except Exception as e:
                            logger.warning(f"Error parsing deadline: {e}")
            
            # Sort by days left (soonest first)
            expiring_rfps.sort(key=lambda x: x['days_left'])
            
            logger.info(f"Found {len(expiring_rfps)} RFPs expiring in the next {days_ahead} days")
            return expiring_rfps
            
        except Exception as e:
            logger.error(f"Error getting expiring RFPs: {str(e)}")
            return []
    
    def estimate_value(self, rfp: Dict) -> Tuple[str, str]:
        """Estimate contract value using GPT-5"""
        try:
            prompt = f"""
            Estimate the contract value for this government RFP:
            
            Title: {rfp.get('title', 'Unknown')}
            Agency: {rfp.get('agency', 'Unknown')}
            NAICS Code: {rfp.get('naics', 'N/A')}
            PSC Code: {rfp.get('psc', 'N/A')}
            Score: {rfp.get('score', 0)}/10
            
            Based on typical government contracts for similar work, provide a realistic value range.
            Consider the agency's typical budget, complexity implied by the title, and industry standards.
            
            Return ONLY the range in format: $XXK-$XXK or $XXM-$XXM (e.g., "$500K-$2M")
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5",  # Using GPT-5 like in scraper
                messages=[
                    {"role": "system", "content": "You are GPT-5, an expert at estimating government contract values based on RFP details."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1,
                max_completion_tokens=5000,  # Much higher limit to avoid truncation
                timeout=30  # 30 second timeout
            )
            
            value_range = response.choices[0].message.content.strip()
            
            # Parse the response to get min and max
            if '-' in value_range:
                parts = value_range.replace('$', '').replace(' ', '').split('-')
                if len(parts) == 2:
                    return f"${parts[0]}", f"${parts[1]}"
            
            # Fallback if parsing fails
            return "$500K", "$2M"
                
        except Exception as e:
            logger.warning(f"GPT-5 value estimation failed: {e}, using NAICS fallback")
            # Fallback to NAICS-based estimation
            naics = rfp.get('naics', '')
            
            if naics.startswith('54'):  # Tech/IT
                return "$500K", "$2M"
            elif naics.startswith('561'):  # Professional services
                return "$250K", "$1M"
            elif naics.startswith('23'):  # Construction
                return "$1M", "$5M"
            elif naics.startswith(('31', '32', '33')):  # Manufacturing
                return "$2M", "$10M"
            else:
                return "$100K", "$500K"
    
    def generate_creative_obituary(self, rfp: Dict) -> Dict:
        """Generate creative obituary elements using GPT-5"""
        try:
            prompt = f"""
            Create a humorous but professional obituary element for this expired government RFP:
            Title: {rfp['title']}
            Agency: {rfp['agency']}
            Score: {rfp['score']}/10
            Days it lived: {rfp.get('days_alive', 30)}
            Why it was good: {rfp.get('justification', 'High potential match')}
            
            Generate:
            1. A witty "last words" quote (max 15 words, as if the RFP could speak)
            2. A "cause of death" diagnosis (max 20 words, use business/medical humor)
            3. One lesson learned (max 20 words, actually educational about RFP management)
            
            Format as JSON with keys: last_words, cause_of_death, lesson
            Be clever but keep it professional and educational.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5",  # Using GPT-5 like in scraper
                messages=[
                    {"role": "system", "content": "You are GPT-5, a witty business writer who creates memorable content about missed opportunities. You must respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1,
                max_completion_tokens=10000,  # Much higher limit to avoid truncation
                response_format={"type": "json_object"},  # Force JSON output
                timeout=30  # 30 second timeout
            )
            
            content = response.choices[0].message.content
            if not content:
                logger.warning("Empty response from GPT-5 for creative obituary")
                raise Exception("Empty response")
            
            content = content.strip()
            # Try to extract JSON from the response (sometimes wrapped in markdown)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as je:
                logger.warning(f"Failed to parse JSON: {content[:200]}")
                # Try to extract JSON-like content
                import re
                match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise je
            
        except Exception as e:
            logger.warning(f"Error generating creative content: {e}")
            # Fallback content
            return {
                "last_words": "I was right there, just needed a click...",
                "cause_of_death": "Death by infinite scroll syndrome",
                "lesson": "Set calendar reminders for high-score RFPs"
            }
    
    def generate_haiku(self, expired_count: int, total_value: str) -> str:
        """Generate a memorial haiku about the week's losses using GPT-5"""
        try:
            prompt = f"""
            Write a haiku about {expired_count} missed business opportunities worth {total_value}.
            Theme: procrastination and missed deadlines in business.
            Make it poignant but slightly funny. Must be exactly 5-7-5 syllables.
            Return just the haiku, no explanation.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-5",  # Using GPT-5 like in scraper
                messages=[
                    {"role": "system", "content": "You are GPT-5, a master haiku writer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1,
                max_completion_tokens=5000,  # Much higher limit to avoid truncation
                timeout=30  # 30 second timeout
            )
            
            return response.choices[0].message.content.strip()
            
        except:
            # Fallback haiku
            return "Deadlines drift past us\nOpportunities fade fast\nRefresh, try again"
    
    def format_slack_obituary(self, expired_rfps: List[Dict], expiring_soon: List[Dict]) -> Dict:
        """Format the obituary as rich Slack blocks with parallel GPT-5 processing"""
        
        blocks = []
        
        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🪦 Weekly RFP Obituary - {datetime.now().strftime('%B %d, %Y')}",
                "emoji": True
            }
        })
        
        blocks.append({"type": "divider"})
        
        # Opening quote
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_\"Here lie the opportunities that slipped through our fingers...\"_"
            }
        })
        
        if not expired_rfps:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🎉 *MIRACLE!* No high-value RFPs died this week! The sheets are working!"
                }
            })
        else:
            # Statistics section
            total_expired = len(expired_rfps)
            perfect_matches_missed = sum(1 for r in expired_rfps if r['score'] >= 9)  # Count both 9/10 and 10/10
            total_min = 0
            total_max = 0
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📊 THE DAMAGE REPORT*\n• Total opportunities lost: {total_expired}\n• Perfect Matches Missed: {perfect_matches_missed}\n• Average score of deceased: {sum(r['score'] for r in expired_rfps)/len(expired_rfps):.1f}/10"
                }
            })
            
            blocks.append({"type": "divider"})
            
            # Individual obituaries (top 3)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*💔 This Week's Most Tragic Departures:*"
                }
            })
            
            # Process all GPT-5 calls in parallel for top 3 RFPs
            top_rfps = expired_rfps[:3]
            rfp_results = {}
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all GPT-5 tasks simultaneously
                futures = {}
                
                for i, rfp in enumerate(top_rfps):
                    # Submit creative obituary generation
                    futures[executor.submit(self.generate_creative_obituary, rfp)] = ('creative', i)
                    # Submit value estimation
                    futures[executor.submit(self.estimate_value, rfp)] = ('value', i)
                
                # Also submit value estimations for expiring RFPs (top 3)
                for i, rfp in enumerate(expiring_soon[:3]):
                    futures[executor.submit(self.estimate_value, rfp)] = ('expiring_value', i)
                
                # We'll calculate total value first before generating haiku
                # (haiku generation moved after totals calculation)
                
                # Collect results as they complete
                for future in as_completed(futures):
                    task_type, index = futures[future]
                    try:
                        result = future.result()
                        if task_type == 'creative':
                            if index not in rfp_results:
                                rfp_results[index] = {}
                            rfp_results[index]['creative'] = result
                        elif task_type == 'value':
                            if index not in rfp_results:
                                rfp_results[index] = {}
                            rfp_results[index]['value'] = result
                        elif task_type == 'expiring_value':
                            if f'expiring_{index}' not in rfp_results:
                                rfp_results[f'expiring_{index}'] = {}
                            rfp_results[f'expiring_{index}']['value'] = result
                    except Exception as e:
                        logger.warning(f"GPT-5 task failed: {e}")
            
            # Now build the obituaries with the parallel results
            for i, rfp in enumerate(top_rfps):
                # Get results from parallel processing
                creative = rfp_results.get(i, {}).get('creative', {
                    "last_words": "I was right there, just needed a click...",
                    "cause_of_death": "Death by infinite scroll syndrome",
                    "lesson": "Set calendar reminders for high-score RFPs"
                })
                
                value_result = rfp_results.get(i, {}).get('value', ("$500K", "$2M"))
                min_val, max_val = value_result if isinstance(value_result, tuple) else ("$500K", "$2M")
                
                # Parse value for totals
                min_num = float(min_val.replace('$', '').replace('K', '000').replace('M', '000000'))
                max_num = float(max_val.replace('$', '').replace('K', '000').replace('M', '000000'))
                total_min += min_num
                total_max += max_num
                
                # Score emoji
                score_emoji = {10: "🏆", 9: "💎", 8: "⭐", 7: "👍"}.get(rfp['score'], "👍")
                
                obituary_text = f"{score_emoji} *\"{rfp['title'][:60]}...\"*\n"
                obituary_text += f"   Agency: {rfp['agency'][:50]}\n"
                obituary_text += f"   Score: {rfp['score_text']} ({rfp['score']}/10) | "
                obituary_text += f"Lived: {rfp.get('days_alive', '?')} days | "
                obituary_text += f"Died: {rfp['deadline']}\n"
                obituary_text += f"   💰 Est. value: {min_val}-{max_val}\n"
                obituary_text += f"   _Last words: \"{creative['last_words']}\"_\n"
                obituary_text += f"   ⚰️ Cause of death: {creative['cause_of_death']}\n"
                obituary_text += f"   📚 *Lesson:* {creative['lesson']}"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": obituary_text
                    }
                })
            
            if len(expired_rfps) > 3:
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"_...and {len(expired_rfps) - 3} other fallen opportunities_"
                    }]
                })
            
            # Format total value
            if total_max >= 1000000:
                total_str = f"${total_min/1000000:.1f}M - ${total_max/1000000:.1f}M"
            else:
                total_str = f"${total_min/1000:.0f}K - ${total_max/1000:.0f}K"
            
            blocks.append({"type": "divider"})
            
            # Generate haiku with GPT-5 in parallel with final formatting
            with ThreadPoolExecutor(max_workers=1) as executor:
                haiku_future = executor.submit(self.generate_haiku, total_expired, total_str)
                haiku = haiku_future.result()
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🎭 MEMORIAL HAIKU*\n```{haiku}```"
                }
            })
            
            # Total estimated loss
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*💸 Total Value Lost:*\n{total_str}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*📈 Opportunity Cost:*\nInfinite"
                    }
                ]
            })
        
        blocks.append({"type": "divider"})
        
        # Death Watch section
        if expiring_soon:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⚠️ DEATH WATCH - {len(expiring_soon)} RFPs EXPIRING THIS WEEK*"
                }
            })
            
            # Show top 3 at risk (using pre-computed values from parallel processing)
            for i, rfp in enumerate(expiring_soon[:3]):
                # Get pre-computed value from parallel results
                value_result = rfp_results.get(f'expiring_{i}', {}).get('value', ("$500K", "$2M"))
                min_val, max_val = value_result if isinstance(value_result, tuple) else ("$500K", "$2M")
                
                day_word = "tomorrow" if rfp['days_left'] == 1 else f"in {rfp['days_left']} days"
                
                risk_text = f"• *{rfp['title'][:60]}*\n"
                risk_text += f"  Dies {day_word} | Score: {rfp['score_text']} | 💰 {min_val}-{max_val}"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": risk_text
                    }
                })
            
            if len(expiring_soon) > 3:
                blocks.append({
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": f"_...plus {len(expiring_soon) - 3} more at risk_"
                    }]
                })
            
            # Call to action with link
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*👀 SAVE THEM BEFORE IT'S TOO LATE:*"
                }
            })
            
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📗 View Crumb Finder Sheet",
                            "emoji": True
                        },
                        "url": f"https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}",
                        "style": "primary"
                    }
                ]
            })
        else:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ *Good news:* No high-value RFPs expiring next week!"
                }
            })
        
        blocks.append({"type": "divider"})
        
        # Footer wisdom
        wisdom = random.choice([
            "\"A deadline missed is a competitor's bliss\"",
            "\"The early bird gets the contract\"",
            "\"An RFP in the hand is worth two in the archive\"",
            "\"Don't let next week's obituary be longer\"",
            "\"Every expired RFP is a lesson in time management\"",
            "\"The best time to submit was yesterday, the second best is today\""
        ])
        
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"_{wisdom}_"
            }]
        })
        
        return {"blocks": blocks}
    
    def send_obituary(self, test_mode: bool = False):
        """Main function to generate and send the obituary"""
        try:
            logger.info("Generating weekly RFP obituary...")
            
            # Get expired RFPs from past week
            expired = self.get_expired_rfps(days_back=7)
            
            # Get RFPs expiring soon
            expiring = self.get_expiring_soon(days_ahead=7)
            
            # Format the obituary
            slack_message = self.format_slack_obituary(expired, expiring)
            
            if test_mode:
                # Just print the message
                logger.info("TEST MODE - Would send to Slack:")
                print(json.dumps(slack_message, indent=2))
                return True
            else:
                # Send to Slack
                success = self.slack.send_raw_message(slack_message)
                
                if success:
                    logger.info(f"✅ Obituary sent! Memorialized {len(expired)} RFPs, warned about {len(expiring)}")
                else:
                    logger.error("Failed to send obituary to Slack")
                
                return success
                
        except Exception as e:
            logger.error(f"Error generating obituary: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run the obituary generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate weekly RFP obituary')
    parser.add_argument('--test', action='store_true', help='Test mode - print instead of sending')
    parser.add_argument('--days', type=int, default=7, help='Days to look back for expired RFPs')
    
    args = parser.parse_args()
    
    obituary = RFPObituary()
    success = obituary.send_obituary(test_mode=args.test)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()