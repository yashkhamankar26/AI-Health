#!/usr/bin/env python3
"""
Debug clinic detection
"""
from dotenv import load_dotenv
load_dotenv()

def debug_detect_clinic_request(message: str):
    """Debug version of detect_clinic_request"""
    message_lower = message.lower()
    print(f"Message: '{message}'")
    print(f"Lowercase: '{message_lower}'")
    
    clinic_keywords = [
        "clinic", "hospital", "doctor", "physician", "medical center",
        "urgent care", "emergency room", "pharmacy", "pharmacies", "dentist", "dentists",
        "find doctor", "find clinic", "find hospital", "healthcare",
        "medical", "health center", "hospitals", "clinics", "doctors"
    ]
    
    location_keywords = ["near", "in", "around", "close to", "nearby"]
    
    # Check for clinic keywords
    found_keywords = [kw for kw in clinic_keywords if kw in message_lower]
    print(f"Found clinic keywords: {found_keywords}")
    
    has_clinic_keyword = any(keyword in message_lower for keyword in clinic_keywords)
    print(f"Has clinic keyword: {has_clinic_keyword}")
    
    if not has_clinic_keyword:
        return False, None, None
    
    # Extract clinic type
    clinic_type = "hospital"
    if "pharmacy" in message_lower or "pharmacies" in message_lower:
        clinic_type = "pharmacy"
    elif "dentist" in message_lower or "dentists" in message_lower:
        clinic_type = "dentist"
    elif "doctor" in message_lower or "doctors" in message_lower or "physician" in message_lower:
        clinic_type = "doctor"
    elif "urgent care" in message_lower:
        clinic_type = "hospital"
    
    print(f"Clinic type: {clinic_type}")
    
    # Extract location
    location = None
    if "near me" in message_lower:
        location = "current_location"
    else:
        # Look for location patterns
        words = message.split()
        print(f"Words: {words}")
        for i, word in enumerate(words):
            print(f"Checking word {i}: '{word}' (lowercase: '{word.lower()}')")
            if word.lower() in location_keywords and i + 1 < len(words):
                print(f"Found location keyword '{word}' at position {i}")
                location_words = []
                for j in range(i + 1, min(i + 4, len(words))):
                    print(f"  Checking location word {j}: '{words[j]}'")
                    if words[j].lower() not in clinic_keywords:
                        location_words.append(words[j])
                        print(f"    Added to location: {words[j]}")
                    else:
                        print(f"    Skipped (clinic keyword): {words[j]}")
                        break
                if location_words:
                    location = " ".join(location_words).strip(".,!?")
                    print(f"Final location: '{location}'")
                break
    
    print(f"Final result: ({has_clinic_keyword}, {location}, {clinic_type})")
    return has_clinic_keyword, location, clinic_type

if __name__ == "__main__":
    debug_detect_clinic_request("Find pharmacies in Chicago")