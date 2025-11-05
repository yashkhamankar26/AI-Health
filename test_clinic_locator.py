#!/usr/bin/env python3
"""
Test script for clinic locator functionality
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
from app.clinic_locator import ClinicLocator, detect_clinic_request, format_clinic_response

async def test_clinic_detection():
    """Test clinic request detection"""
    print("🧪 Testing clinic request detection...")
    
    test_messages = [
        "Find hospitals near me",
        "I need a doctor in New York",
        "Show me clinics in Chicago",
        "Where can I find a pharmacy in 90210?",
        "Find urgent care centers in Los Angeles",
        "What is diabetes?",  # Should not be detected as clinic request
        "How to treat a headache?"  # Should not be detected as clinic request
    ]
    
    for message in test_messages:
        is_clinic, location, clinic_type = detect_clinic_request(message)
        print(f"'{message}' -> Clinic: {is_clinic}, Location: {location}, Type: {clinic_type}")

async def test_clinic_search():
    """Test clinic search functionality"""
    print("\n🏥 Testing clinic search...")
    
    clinic_locator = ClinicLocator()
    
    # Test with a known location
    test_location = "New York, NY"
    print(f"Searching for hospitals in {test_location}...")
    
    clinics = await clinic_locator.search_clinics_by_location(test_location, "hospital")
    
    if clinics:
        print(f"✓ Found {len(clinics)} hospitals")
        for i, clinic in enumerate(clinics[:3], 1):  # Show first 3
            print(f"  {i}. {clinic['name']} - {clinic['address']} (Rating: {clinic['rating']})")
        
        # Test response formatting
        response = await format_clinic_response(clinics[:5], test_location, "hospital")
        print(f"\n📝 Formatted response:\n{response[:200]}...")
    else:
        print("✗ No clinics found (API key might be missing or invalid)")

if __name__ == "__main__":
    asyncio.run(test_clinic_detection())
    asyncio.run(test_clinic_search())