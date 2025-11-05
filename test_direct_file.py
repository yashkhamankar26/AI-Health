#!/usr/bin/env python3
"""
Test by reading file directly
"""

# Read and execute the file directly
with open('app/clinic_locator.py', 'r') as f:
    content = f.read()

# Execute the content
exec(content)

# Test the function
result = detect_clinic_request("Find pharmacies in Chicago")
print(f"Result: {result}")

# Also test the debug version
message = "Find pharmacies in Chicago"
message_lower = message.lower()
clinic_keywords = [
    "clinic", "hospital", "doctor", "physician", "medical center",
    "urgent care", "emergency room", "pharmacy", "pharmacies", "dentist", "dentists",
    "find doctor", "find clinic", "find hospital", "healthcare",
    "medical", "health center", "hospitals", "clinics", "doctors"
]

found_keywords = [kw for kw in clinic_keywords if kw in message_lower]
print(f"Found keywords: {found_keywords}")
print(f"'pharmacies' in message_lower: {'pharmacies' in message_lower}")
print(f"'pharmacy' in message_lower: {'pharmacy' in message_lower}")