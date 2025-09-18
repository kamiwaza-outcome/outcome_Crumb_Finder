#!/usr/bin/env python3
"""
Test GPT-5-mini reasoning tokens behavior
"""

import openai
import json
from config import Config

client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

def test_reasoning_tokens():
    """Test how reasoning tokens affect GPT-5-mini responses"""
    
    print("\n" + "="*70)
    print("🧠 TESTING GPT-5-MINI REASONING TOKENS")
    print("="*70)
    
    # Test with different token limits
    token_limits = [100, 200, 300, 500, 1000]
    
    test_prompt = """Score this RFP from 1-10 for relevance to AI/data/software companies.

RFP: Custom Computer Programming Services for data analytics platform
Agency: Department of Defense
NAICS: 541512

Respond with JSON only:
{
    "score": 1-10,
    "reason": "One sentence explanation"
}"""
    
    for limit in token_limits:
        print(f"\n📊 Testing with max_completion_tokens={limit}")
        try:
            response = client.chat.completions.create(
                model='gpt-5-mini',
                messages=[
                    {"role": "system", "content": "You are a rapid RFP screener. Respond only with JSON."},
                    {"role": "user", "content": test_prompt}
                ],
                max_completion_tokens=limit,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            usage = response.usage
            
            print(f"   Response content: '{content}'")
            print(f"   Completion tokens: {usage.completion_tokens}")
            print(f"   Reasoning tokens: {usage.completion_tokens_details.reasoning_tokens}")
            print(f"   Actual output tokens: {usage.completion_tokens - usage.completion_tokens_details.reasoning_tokens}")
            
            if content:
                try:
                    parsed = json.loads(content)
                    print(f"   ✓ Valid JSON: {parsed}")
                except:
                    print(f"   ✗ Invalid JSON")
            else:
                print(f"   ✗ Empty response")
                
        except Exception as e:
            print(f"   ✗ Error: {str(e)[:100]}")
    
    print("\n" + "="*70)
    print("💡 CONCLUSION:")
    print("GPT-5-mini uses internal reasoning tokens before generating output.")
    print("We need to set max_completion_tokens higher to account for this!")
    print("="*70)

if __name__ == "__main__":
    test_reasoning_tokens()