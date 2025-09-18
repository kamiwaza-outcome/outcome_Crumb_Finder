#!/usr/bin/env python3
"""
Diagnostic script to test GPT-5-mini responses
"""

import openai
import json
import os
from config import Config

# Initialize OpenAI client
client = openai.OpenAI(
    api_key=Config.OPENAI_API_KEY,
    max_retries=3,
    timeout=30
)

def test_gpt5_mini():
    """Test different configurations with GPT-5-mini"""
    
    print("\n" + "="*70)
    print("🔍 TESTING GPT-5-MINI CONFIGURATIONS")
    print("="*70)
    
    # Test 1: Basic completion without JSON format
    print("\n1. Testing basic completion (no JSON format)...")
    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Rate this RFP from 1-10: 'Software development services'. Reply with just a number and brief reason."}
            ],
            max_completion_tokens=50
        )
        print(f"   ✓ Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
    
    # Test 2: JSON format with response_format
    print("\n2. Testing with JSON response format...")
    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[
                {"role": "system", "content": "You are a rapid RFP screener. Respond only with JSON."},
                {"role": "user", "content": 'Score this RFP from 1-10: "Software development". Return JSON: {"score": N, "reason": "..."}'}
            ],
            max_completion_tokens=100,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        print(f"   Raw response: '{content}'")
        if content:
            parsed = json.loads(content)
            print(f"   ✓ Parsed JSON: {parsed}")
        else:
            print(f"   ✗ Empty response received")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
    
    # Test 3: Without response_format parameter
    print("\n3. Testing JSON without response_format parameter...")
    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[
                {"role": "system", "content": "Respond with valid JSON only."},
                {"role": "user", "content": 'Rate 1-10: "AI software". Reply: {"score": N, "reason": "text"}'}
            ],
            max_completion_tokens=100
        )
        content = response.choices[0].message.content
        print(f"   Raw response: '{content}'")
        if content:
            parsed = json.loads(content)
            print(f"   ✓ Parsed JSON: {parsed}")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
    
    # Test 4: Try with temperature=0 for deterministic output
    print("\n4. Testing with temperature=0...")
    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[
                {"role": "system", "content": "You must respond with JSON: {\"score\": number, \"reason\": string}"},
                {"role": "user", "content": "Rate this: 'Cloud computing services'"}
            ],
            max_completion_tokens=100,
            temperature=0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        print(f"   Raw response: '{content}'")
        if content:
            print(f"   ✓ Response received: {json.loads(content)}")
        else:
            print(f"   ✗ Empty response")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
    
    # Test 5: Check if it's a token limit issue
    print("\n5. Testing with higher token limit...")
    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[
                {"role": "user", "content": "Output exactly this JSON: {\"test\": \"hello\"}"}
            ],
            max_completion_tokens=500  # Higher limit
        )
        content = response.choices[0].message.content
        print(f"   Response: '{content}'")
        print(f"   Usage: {response.usage}")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
    
    # Test 6: Check the actual response object structure
    print("\n6. Checking full response object structure...")
    try:
        response = client.chat.completions.create(
            model='gpt-5-mini',
            messages=[
                {"role": "user", "content": "Say 'test'"}
            ],
            max_completion_tokens=10
        )
        print(f"   Model: {response.model}")
        print(f"   Choices: {len(response.choices)}")
        print(f"   Message role: {response.choices[0].message.role}")
        print(f"   Message content: '{response.choices[0].message.content}'")
        print(f"   Finish reason: {response.choices[0].finish_reason}")
        print(f"   Usage: {response.usage}")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
    
    print("\n" + "="*70)
    print("✨ Diagnostic complete")
    print("="*70)

if __name__ == "__main__":
    test_gpt5_mini()