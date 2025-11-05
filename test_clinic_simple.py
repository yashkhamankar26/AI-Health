#!/usr/bin/env python3
"""
Simple test for clinic functionality
"""
import asyncio
import httpx

async def test_clinic_chat():
    """Test clinic functionality through the chat API"""
    
    # First login
    login_data = {
        "email": "demo@healthcare.com",
        "password": "demo123"
    }
    
    async with httpx.AsyncClient() as client:
        # Login
        login_response = await client.post("http://localhost:8000/api/login", json=login_data)
        if login_response.status_code != 200:
            print("❌ Login failed")
            return
        
        token = login_response.json()["token"]
        print("✅ Login successful")
        
        # Test clinic requests
        test_messages = [
            "Find hospitals in New York",
            "I need a doctor in Chicago", 
            "Show me clinics near me",
            "Find pharmacies in Los Angeles"
        ]
        
        for message in test_messages:
            chat_data = {
                "message": message,
                "token": token
            }
            
            chat_response = await client.post("http://localhost:8000/api/chat", json=chat_data)
            
            if chat_response.status_code == 200:
                reply = chat_response.json()["reply"]
                print(f"\n🔍 Query: {message}")
                print(f"📝 Response: {reply[:100]}...")
            else:
                print(f"❌ Chat failed for: {message}")

if __name__ == "__main__":
    asyncio.run(test_clinic_chat())