#!/usr/bin/env python3
"""
Final test of clinic locator functionality
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys
import os

# Force reload by removing from cache
if 'app.clinic_locator' in sys.modules:
    del sys.modules['app.clinic_locator']

from app.clinic_locator import detect_clinic_request, search_clinics_by_location, format_clinic_response

async def test_clinic_functionality():
    """Test complete clinic functionality"""
    print("🏥 Final Clinic Locator Test")
    print("=" * 50)
    
    test_cases = [
        "Find hospitals near me",
        "I need a doctor in New York", 
        "Show me clinics in Chicago",
        "Find pharmacies in Chicago",
        "Where can I find a dentist in Los Angeles?",
        "What is diabetes?",  # Should not be detected
    ]
    
    for message in test_cases:
        print(f"\n📝 Testing: '{message}'")
        
        # Step 1: Detection
        is_clinic, location, clinic_type = detect_clinic_request(message)
        
        if is_clinic:
            print(f"   ✅ Detected: {clinic_type} in {location}")
            
            # Step 2: Search (only for real locations, not "current_location")
            if location and location != "current_location":
                try:
                    clinics = await search_clinics_by_location(location, clinic_type)
                    if clinics:
                        print(f"   🏥 Found {len(clinics)} results")
                        print(f"   📍 Top result: {clinics[0]['name']} - {clinics[0]['address']}")
                    else:
                        print(f"   ❌ No results found")
                except Exception as e:
                    print(f"   ❌ Search error: {e}")
            else:
                print(f"   ⏭️  Skipping search (location: {location})")
        else:
            print(f"   ❌ Not a clinic request")

if __name__ == "__main__":
    asyncio.run(test_clinic_functionality())