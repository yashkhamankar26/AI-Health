#!/usr/bin/env python3
"""
Test clinic locator integration with the running server
"""
import asyncio
import httpx

async def test_clinic_chat():
    """Test clinic requests through the chat API"""
    print("🏥 Testing clinic locator through chat API...")
    
    test_messages = [
        "Find hospitals in New York",
        "I need a pharmacy in Chicago", 
        "Show me dentists in Los Angeles",
        "Find clinics near me",
        "What is diabetes?"  # Should not trigger clinic locator
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for message in test_messages:
            print(f"\n📝 Testing: '{message}'")
            
            try:
                response = await client.post(
                    "http://localhost:4000/api/chat",
                    json={"message": message}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    reply = data.get("reply", "No reply")
                    
                    # Check if it's a clinic response
                    if any(word in reply.lower() for word in ["found", "clinic", "hospital", "pharmacy", "dentist"]):
                        print(f"   ✅ Clinic response: {reply[:100]}...")
                    else:
                        print(f"   🤖 AI response: {reply[:100]}...")
                else:
                    print(f"   ❌ Error {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_clinic_chat())