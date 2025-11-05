#!/usr/bin/env python3
"""
Direct test of clinic_locator functions
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Try to import the module
    print("Attempting to import app.clinic_locator...")
    import app.clinic_locator as clinic_mod
    print(f"Module imported successfully. Available functions: {dir(clinic_mod)}")
    
    # Try to import specific function
    print("Attempting to import detect_clinic_request...")
    from app.clinic_locator import detect_clinic_request
    print("Function imported successfully!")
    
    # Test the function
    test_message = "Find hospitals near me"
    result = detect_clinic_request(test_message)
    print(f"Test result for '{test_message}': {result}")
    
except ImportError as e:
    print(f"Import error: {e}")
    
    # Let's try to read and execute the file directly
    print("\nTrying to read file directly...")
    try:
        with open('app/clinic_locator.py', 'r') as f:
            content = f.read()
            print(f"File content length: {len(content)} characters")
            if len(content) > 0:
                print("First 200 characters:")
                print(content[:200])
            else:
                print("File is empty!")
    except Exception as file_error:
        print(f"Error reading file: {file_error}")

except Exception as e:
    print(f"Other error: {e}")