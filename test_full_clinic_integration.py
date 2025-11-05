#!/usr/bin/env python3
"""
Test full clinic locator integration with Google Maps API
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
from app.clinic_locator import detect_clinic_request, search_clinics_by_location, format_clinic_response

async def test_full_integration():
    """Test the complete clinic locator workflow"""
    print("🏥 Testing full clinic locator integration...")
    
    # Test message
    test_message = "Find hospitals in New York"
    print(f"Test message: '{test_message}'")
    
    # Step 1: Detect clinic request
    is_clinic, location, clinic_type = detect_clinic_request(test_message)
    print(f"✅ Detection: Clinic={is_clinic}, Location={location}, Type={clinic_type}")
    
    if is_clinic and location:
        # Step 2: Search for clinics
        print(f"🔍 Searching for {clinic_type}s in {location}...")
        clinics = await search_clinics_by_location(location, clinic_type)
        print(f"✅ Found {len(clinics)} clinics")
        
        if clinics:
            # Show first few results
            for i, clinic in enumerate(clinics[:3], 1):
                print(f"  {i}. {clinic['name']} - {clinic['address']} (Rating: {clinic['rating']})")
            
            # Step 3: Format response
            response = format_clinic_response(clinics, location, clinic_type)
            print(f"\n📝 Formatted response:\n{response[:300]}...")
        else:
            print("❌ No clinics found")
    else:
        print("❌ Not a clinic request or no location detected")

async def test_different_locations():
    """Test with different locations and clinic types"""
    print("\n🌍 Testing different locations and clinic types...")
    
    test_cases = [
        ("Find pharmacies in Chicago", "Chicago", "pharmacy"),
        ("I need a dentist in Los Angeles", "Los Angeles", "dentist"),
        ("Show me doctors in Boston", "Boston", "doctor")
    ]
    
    for message, expected_location, expected_type in test_cases:
        print(f"\n📍 Testing: '{message}'")
        is_clinic, location, clinic_type = detect_clinic_request(message)
        
        if is_clinic and location:
            clinics = await search_clinics_by_location(location, clinic_type)
            print(f"   ✅ Found {len(clinics)} {clinic_type}s in {location}")
        else:
            print(f"   ❌ Detection failed")

if __name__ == "__main__":
    asyncio.run(test_full_integration())
    asyncio.run(test_different_locations())