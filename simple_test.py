#!/usr/bin/env python3
"""
Simple test for clinic detection
"""
import sys
sys.path.append('.')

from app.clinic_locator import detect_clinic_request

def test_detection():
    test_messages = [
        "Find hospitals near me",
        "I need a doctor in New York", 
        "Show me clinics in Chicago",
        "What is diabetes?"
    ]
    
    for message in test_messages:
        is_clinic, location, clinic_type = detect_clinic_request(message)
        print(f"'{message}' -> Clinic: {is_clinic}, Location: {location}, Type: {clinic_type}")

if __name__ == "__main__":
    test_detection()