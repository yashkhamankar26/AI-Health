"""
Clinic location service using Google Maps Places API.
"""

import os
from typing import List, Dict, Optional, Tuple
import httpx

# Google Maps API configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GOOGLE_PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
GOOGLE_GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

def detect_clinic_request(message: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Detect if user is asking for clinic recommendations."""
    message_lower = message.lower()
    
    clinic_keywords = [
        "clinic", "hospital", "doctor", "physician", "medical center",
        "urgent care", "emergency room", "pharmacy", "pharmacies", "dentist", "dentists",
        "find doctor", "find clinic", "find hospital", "healthcare",
        "medical", "health center", "hospitals", "clinics", "doctors"
    ]
    
    location_keywords = ["near", "in", "around", "close to", "nearby"]
    
    has_clinic_keyword = any(keyword in message_lower for keyword in clinic_keywords)
    
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
    
    # Extract location
    location = None
    if "near me" in message_lower:
        location = "current_location"
    else:
        # Look for location patterns
        words = message.split()
        for i, word in enumerate(words):
            if word.lower() in location_keywords and i + 1 < len(words):
                location_words = []
                for j in range(i + 1, min(i + 4, len(words))):
                    if words[j].lower() not in clinic_keywords:
                        location_words.append(words[j])
                    else:
                        break
                if location_words:
                    location = " ".join(location_words).strip(".,!?")
                break
    
    return True, location, clinic_type

async def search_clinics_by_location(location: str, clinic_type: str = "hospital") -> List[Dict]:
    """Search for clinics by location using Google Maps Places API."""
    if not GOOGLE_MAPS_API_KEY:
        print("❌ Google Maps API key not found")
        return []
    
    try:
        # First, geocode the location to get coordinates
        async with httpx.AsyncClient(timeout=30.0) as client:
            geocode_params = {
                "address": location,
                "key": GOOGLE_MAPS_API_KEY
            }
            
            geocode_response = await client.get(GOOGLE_GEOCODING_API_URL, params=geocode_params)
            geocode_data = geocode_response.json()
            
            if geocode_data["status"] != "OK" or not geocode_data["results"]:
                print(f"❌ Could not geocode location: {location}")
                return []
            
            # Get coordinates
            coords = geocode_data["results"][0]["geometry"]["location"]
            lat, lng = coords["lat"], coords["lng"]
            
            # Map clinic types to Google Places types
            type_mapping = {
                "hospital": "hospital",
                "pharmacy": "pharmacy", 
                "dentist": "dentist",
                "doctor": "doctor"
            }
            
            places_type = type_mapping.get(clinic_type, "hospital")
            
            # Search for places
            places_params = {
                "location": f"{lat},{lng}",
                "radius": 5000,  # 5km radius
                "type": places_type,
                "key": GOOGLE_MAPS_API_KEY
            }
            
            places_response = await client.get(GOOGLE_PLACES_API_URL, params=places_params)
            places_data = places_response.json()
            
            if places_data["status"] != "OK":
                print(f"❌ Places API error: {places_data.get('status')}")
                return []
            
            # Format results
            clinics = []
            for place in places_data.get("results", [])[:10]:  # Limit to 10 results
                clinic = {
                    "name": place.get("name", "Unknown"),
                    "address": place.get("vicinity", "Address not available"),
                    "rating": place.get("rating", 0),
                    "rating_count": place.get("user_ratings_total", 0),
                    "types": place.get("types", []),
                    "open_now": place.get("opening_hours", {}).get("open_now", None)
                }
                clinics.append(clinic)
            
            return clinics
            
    except Exception as e:
        print(f"❌ Error searching for clinics: {e}")
        return []

def format_clinic_response(clinics: List[Dict], location: str, clinic_type: str) -> str:
    """Format clinic search results into a user-friendly response."""
    if not clinics:
        return f"I couldn't find any {clinic_type}s near {location}. You might want to try:\n• Checking Google Maps directly\n• Contacting your insurance provider for in-network options\n• Calling 211 for local healthcare resources"
    
    response_parts = [f"I found {len(clinics)} {clinic_type}{'s' if len(clinics) > 1 else ''} near {location}:\n"]
    
    for i, clinic in enumerate(clinics, 1):
        clinic_info = f"{i}. **{clinic['name']}**"
        if clinic.get('address'):
            clinic_info += f"\n   📍 {clinic['address']}"
        if clinic.get('rating', 0) > 0:
            clinic_info += f"\n   ⭐ {clinic['rating']}/5 ({clinic['rating_count']} reviews)"
        if clinic.get('open_now') is not None:
            status = "🟢 Open now" if clinic['open_now'] else "🔴 Closed now"
            clinic_info += f"\n   {status}"
        response_parts.append(clinic_info)
    
    response_parts.append("\n💡 **Tip**: Call ahead to confirm hours and availability, and check if they accept your insurance.")
    return "\n\n".join(response_parts)