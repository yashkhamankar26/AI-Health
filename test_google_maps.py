#!/usr/bin/env python3
"""
Test Google Maps API functionality
"""
from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
import httpx

async def test_google_maps_api():
    """Test Google Maps API directly"""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not api_key:
        print("❌ No Google Maps API key found")
        return
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test geocoding
            geocode_params = {
                "address": "New York, NY",
                "key": api_key
            }
            
            print("🌍 Testing geocoding...")
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=geocode_params
            )
            
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"API Status: {data.get('status')}")
            
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                print(f"✅ Geocoded New York to: {location['lat']}, {location['lng']}")
                
                # Test places search
                places_params = {
                    "location": f"{location['lat']},{location['lng']}",
                    "radius": 5000,
                    "type": "hospital",
                    "key": api_key
                }
                
                print("🏥 Testing places search...")
                places_response = await client.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params=places_params
                )
                
                places_data = places_response.json()
                print(f"Places Status: {places_data.get('status')}")
                
                if places_data.get('status') == 'OK':
                    results = places_data.get('results', [])
                    print(f"✅ Found {len(results)} hospitals")
                    for i, place in enumerate(results[:3], 1):
                        print(f"  {i}. {place.get('name')} - {place.get('vicinity')}")
                else:
                    print(f"❌ Places API error: {places_data.get('error_message', 'Unknown error')}")
            else:
                print(f"❌ Geocoding error: {data.get('error_message', 'Unknown error')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_google_maps_api())