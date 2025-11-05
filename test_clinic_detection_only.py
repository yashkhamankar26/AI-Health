#!/usr/bin/env python3
"""
Test script for clinic detection functionality only
"""
from dotenv import load_dotenv
load_dotenv()

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.clinic_locator import detect_clinic_request

def test_clinic_detection():
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
        status = "✅" if is_clinic else "❌"
        print(f"{status} '{message}' -> Clinic: {is_clinic}, Location: {location}, Type: {clinic_type}")

if __name__ == "__main__":
    test_clinic_detection()