#!/usr/bin/env python3
"""
Debug script to test OpenAI API configuration
"""
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import os
import asyncio

# Check if httpx is available
try:
    import httpx
    print("✓ httpx is available")
    HTTPX_AVAILABLE = True
except ImportError as e:
    print(f"✗ httpx is NOT available: {e}")
    HTTPX_AVAILABLE = False

# Check environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(f"✓ API Key loaded: {'Yes' if OPENAI_API_KEY else 'No'}")
if OPENAI_API_KEY:
    print(f"✓ API Key format: {OPENAI_API_KEY[:10]}...{OPENAI_API_KEY[-10:] if len(OPENAI_API_KEY) > 20 else OPENAI_API_KEY}")

async def test_openai_api():
    """Test OpenAI API call"""
    if not OPENAI_API_KEY or not HTTPX_AVAILABLE:
        print("✗ Cannot test API - missing requirements")
        return
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a healthcare AI assistant."},
                    {"role": "user", "content": "What is a headache?"}
                ],
                "temperature": 0.2,
                "max_tokens": 100
            }
            
            print("🔄 Testing OpenAI API call...")
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            print(f"✓ Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    ai_response = data["choices"][0]["message"]["content"].strip()
                    print(f"✓ API Response: {ai_response[:100]}...")
                    return True
                else:
                    print("✗ No choices in response")
                    print(f"Response: {data}")
            elif response.status_code == 401:
                print("✗ Authentication failed - invalid API key")
            elif response.status_code == 429:
                print("✗ Rate limit exceeded")
            else:
                print(f"✗ API error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
            
    except Exception as e:
        print(f"✗ Exception during API call: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_openai_api())