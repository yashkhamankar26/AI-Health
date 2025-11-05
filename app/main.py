"""
Main FastAPI application for Healthcare Chatbot MVP.

This module contains the central FastAPI application with authentication
and chat endpoints, implementing secure token-based authentication.
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import secrets
import os
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

import asyncio
import json
from typing import Dict, Set, Optional

from .models import LoginIn, LoginOut, ChatIn, ChatOut
from .security import hash_for_logging
from .content_filter import should_process_query, get_refusal_message
try:
    from .db import get_db, ChatLog, SessionLocal, init_database
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    get_db = None
    ChatLog = None
    SessionLocal = None
    init_database = None

# Initialize FastAPI application
app = FastAPI(
    title="Healthcare Chatbot MVP",
    description="AI-powered healthcare assistance with secure authentication",
    version="1.0.0"
)

# Global exception handlers for better error handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with user-friendly messages."""
    errors = []
    for error in exc.errors():
        field = error.get('loc', ['unknown'])[-1]
        message = error.get('msg', 'Invalid input')
        
        # Convert technical error messages to user-friendly ones
        if 'field required' in message.lower():
            message = f"{field.title()} is required"
        elif 'string should have at least' in message.lower():
            if field == 'message':
                message = "Message cannot be empty"
            else:
                message = f"{field.title()} is too short"
        elif 'string should have at most' in message.lower():
            if field == 'message':
                message = "Message is too long. Please keep it under 1000 characters."
            else:
                message = f"{field.title()} is too long"
        elif 'value is not a valid email address' in message.lower():
            message = "Please enter a valid email address"
        elif 'ensure this value has at least' in message.lower():
            if field == 'message':
                message = "Message cannot be empty"
            else:
                message = f"{field.title()} is too short"
        elif 'ensure this value has at most' in message.lower():
            if field == 'message':
                message = "Message is too long. Please keep it under 1000 characters."
            else:
                message = f"{field.title()} is too long"
        
        errors.append({
            'field': field,
            'message': message
        })
    
    # Return the first error for simplicity
    if errors:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'detail': errors[0]['message']}
        )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={'detail': 'Invalid input provided'}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions with user-friendly messages."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={'detail': str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully."""
    print(f"Unexpected error: {exc}")  # Log for debugging
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={'detail': 'An unexpected error occurred. Please try again later.'}
    )

@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    if DB_AVAILABLE and init_database:
        try:
            init_database()
        except Exception as e:
            print(f"Warning: Database initialization failed: {e}")

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Demo credentials for MVP authentication
DEMO_CREDENTIALS = {
    "demo@healthcare.com": "demo123",
    "user@example.com": "password123"
}

# In-memory token storage for MVP (use proper session management in production)
active_tokens: Set[str] = set()

# Google Maps API configuration for clinic location
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def detect_clinic_request(message: str) -> tuple[bool, str, str]:
    """Detect if user is asking for clinic recommendations."""
    message_lower = message.lower()
    
    # Expanded clinic keywords for better detection
    clinic_keywords = [
        "clinic", "hospital", "doctor", "physician", "medical center",
        "urgent care", "emergency room", "pharmacy", "dentist",
        "find doctor", "find clinic", "find hospital", "medical facility",
        "healthcare provider", "medical practice", "specialist", "health center",
        "walk-in clinic", "family doctor", "general practitioner", "gp",
        "medical office", "healthcare facility", "treatment center"
    ]
    
    # Location indicators
    location_indicators = [
        "near me", "nearby", "close to", "in my area", "around",
        "near", "close", "local", "in", "at", "around"
    ]
    
    has_clinic_keyword = any(keyword in message_lower for keyword in clinic_keywords)
    
    if not has_clinic_keyword:
        return False, None, None
    
    print(f"🔍 Clinic request detected: {message}")  # Debug log
    
    # Extract clinic type with more specific matching
    clinic_type = "hospital"  # default
    if any(word in message_lower for word in ["pharmacy", "drug store", "drugstore"]):
        clinic_type = "pharmacy"
    elif any(word in message_lower for word in ["dentist", "dental", "orthodontist"]):
        clinic_type = "dentist"
    elif any(word in message_lower for word in ["urgent care", "walk-in", "emergency"]):
        clinic_type = "hospital"
    elif any(word in message_lower for word in ["doctor", "physician", "gp", "general practitioner", "family doctor"]):
        clinic_type = "doctor"
    elif any(word in message_lower for word in ["specialist", "cardiologist", "dermatologist"]):
        clinic_type = "doctor"
    
    # Enhanced location extraction
    location = None
    if any(phrase in message_lower for phrase in ["near me", "nearby", "close to me", "in my area"]):
        location = "current_location"
    else:
        # Try multiple patterns for location extraction
        words = message.split()
        
        # Pattern 1: "in [location]"
        for i, word in enumerate(words):
            if word.lower() in ["in", "near", "around", "at"] and i + 1 < len(words):
                location_words = []
                for j in range(i + 1, min(i + 4, len(words))):  # Take up to 3 words
                    if words[j].lower() not in ["me", "my", "area", "the"]:
                        location_words.append(words[j])
                    else:
                        break
                if location_words:
                    location = " ".join(location_words).strip(".,!?")
                    break
        
        # Pattern 2: If no location found, try to find city/state patterns
        if not location:
            # Look for common city patterns (word followed by state abbreviation or "city")
            for i, word in enumerate(words):
                if i + 1 < len(words):
                    next_word = words[i + 1].upper()
                    # Check for state abbreviations
                    if len(next_word) == 2 and next_word.isalpha():
                        location = f"{word} {next_word}"
                        break
                    elif next_word in ["CITY", "COUNTY"]:
                        location = word
                        break
    
    print(f"📍 Extracted location: {location}, type: {clinic_type}")  # Debug log
    return True, location, clinic_type

async def search_clinics_by_location(location: str, clinic_type: str = "hospital") -> list:
    """Search for clinics using Google Maps API."""
    print(f"🔍 Searching for {clinic_type}s in {location}")  # Debug log
    
    if not GOOGLE_MAPS_API_KEY:
        print("❌ No Google Maps API key found")
        return []
    
    if not HTTPX_AVAILABLE:
        print("❌ httpx not available")
        return []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Geocode the location
            geocode_params = {
                "address": location,
                "key": GOOGLE_MAPS_API_KEY
            }
            
            print(f"🌍 Geocoding location: {location}")
            geocode_response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=geocode_params
            )
            
            print(f"📍 Geocoding response status: {geocode_response.status_code}")
            
            if geocode_response.status_code != 200:
                print(f"❌ Geocoding failed with status {geocode_response.status_code}")
                return []
            
            geocode_data = geocode_response.json()
            print(f"📍 Geocoding status: {geocode_data.get('status')}")
            
            if geocode_data.get("status") != "OK":
                print(f"❌ Geocoding API error: {geocode_data.get('status')} - {geocode_data.get('error_message', 'Unknown error')}")
                return []
            
            if not geocode_data.get("results"):
                print("❌ No geocoding results found")
                return []
            
            location_data = geocode_data["results"][0]["geometry"]["location"]
            lat, lng = location_data["lat"], location_data["lng"]
            print(f"✅ Geocoded to: {lat}, {lng}")
            
            # Step 2: Search for nearby places
            type_mapping = {
                "hospital": "hospital",
                "clinic": "hospital", 
                "doctor": "doctor",
                "pharmacy": "pharmacy",
                "dentist": "dentist"
            }
            
            place_type = type_mapping.get(clinic_type.lower(), "hospital")
            print(f"🏥 Searching for place type: {place_type}")
            
            places_params = {
                "location": f"{lat},{lng}",
                "radius": 10000,  # Increased radius to 10km
                "type": place_type,
                "key": GOOGLE_MAPS_API_KEY
            }
            
            places_response = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params=places_params
            )
            
            print(f"🏥 Places response status: {places_response.status_code}")
            
            if places_response.status_code != 200:
                print(f"❌ Places search failed with status {places_response.status_code}")
                return []
            
            places_data = places_response.json()
            print(f"🏥 Places API status: {places_data.get('status')}")
            
            if places_data.get("status") != "OK":
                print(f"❌ Places API error: {places_data.get('status')} - {places_data.get('error_message', 'Unknown error')}")
                return []
            
            results = places_data.get("results", [])
            print(f"✅ Found {len(results)} places")
            
            # Format results
            clinics = []
            for place in results[:8]:  # Increased to 8 results
                clinic = {
                    "name": place.get("name", "Unknown"),
                    "address": place.get("vicinity", place.get("formatted_address", "Address not available")),
                    "rating": place.get("rating", 0),
                    "rating_count": place.get("user_ratings_total", 0),
                    "open_now": place.get("opening_hours", {}).get("open_now", None),
                    "place_id": place.get("place_id", ""),
                    "types": place.get("types", [])
                }
                clinics.append(clinic)
                print(f"  📋 {clinic['name']} - {clinic['address']}")
            
            return clinics
            
    except httpx.TimeoutException:
        print("❌ Request timed out")
        return []
    except httpx.ConnectError:
        print("❌ Connection error")
        return []
    except Exception as e:
        print(f"❌ Unexpected error in clinic search: {e}")
        import traceback
        traceback.print_exc()
        return []

def format_clinic_response(clinics: list, location: str, clinic_type: str) -> str:
    """Format clinic search results into a user-friendly response."""
    if not clinics:
        return f"I couldn't find any {clinic_type}s near {location}. This might be because:\n\n• The location wasn't recognized - try being more specific (e.g., 'New York, NY' instead of just 'New York')\n• There are no {clinic_type}s in the immediate area\n• The Google Maps API might be experiencing issues\n\nYou can also try:\n• Searching on Google Maps directly\n• Checking your insurance provider's website\n• Calling your insurance company for in-network providers"
    
    # Create a more detailed response
    facility_name = clinic_type.replace("_", " ").title()
    if clinic_type == "doctor":
        facility_name = "Medical Practice"
    elif clinic_type == "hospital":
        facility_name = "Hospital/Medical Center"
    
    response_parts = [
        f"🏥 **{facility_name}s near {location.title()}**\n",
        f"I found {len(clinics)} healthcare facilities for you:\n"
    ]
    
    for i, clinic in enumerate(clinics, 1):
        clinic_info = f"**{i}. {clinic['name']}**"
        
        if clinic['address']:
            clinic_info += f"\n   📍 **Address:** {clinic['address']}"
        
        if clinic['rating'] > 0:
            stars = "⭐" * min(int(clinic['rating']), 5)
            clinic_info += f"\n   {stars} **Rating:** {clinic['rating']}/5.0"
            if clinic['rating_count'] > 0:
                clinic_info += f" ({clinic['rating_count']} reviews)"
        
        if clinic['open_now'] is not None:
            status = "🟢 **Open now**" if clinic['open_now'] else "🔴 **Closed now**"
            clinic_info += f"\n   {status}"
        
        # Add facility type information
        if clinic.get('types'):
            relevant_types = [t.replace('_', ' ').title() for t in clinic['types'] 
                            if t in ['hospital', 'doctor', 'pharmacy', 'dentist', 'health']]
            if relevant_types:
                clinic_info += f"\n   🏷️ **Type:** {', '.join(relevant_types[:2])}"
        
        response_parts.append(clinic_info)
    
    # Add helpful footer
    response_parts.extend([
        "\n" + "="*50,
        "💡 **Important Tips:**",
        "• Call ahead to confirm hours and availability",
        "• Check if they accept your insurance",
        "• Ask about appointment availability",
        "• For emergencies, call 911 or go to the nearest ER",
        "\n🔍 **Need more options?** Try searching for a broader area or different facility type."
    ])
    
    return "\n\n".join(response_parts)

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TEMPERATURE = 0.2
OPENAI_TIMEOUT = 30.0

# Load healthcare system prompt
def load_system_prompt() -> str:
    """Load the healthcare-focused system prompt from file."""
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "You are a healthcare AI assistant. Only respond to healthcare-related queries."

SYSTEM_PROMPT = load_system_prompt()

# Token generation for demo mode
def generate_demo_token(email: str) -> str:
    """
    Generate a demo authentication token.
    
    Args:
        email (str): User's email address
        
    Returns:
        str: Generated authentication token
    """
    # Create a simple but unique token for demo purposes
    token_data = f"demo_{email}_{secrets.token_hex(8)}"
    return hash_for_logging(token_data, use_hmac=False)[:32]


def validate_credentials(email: str, password: str) -> bool:
    """
    Validate user credentials against demo credentials.
    
    Args:
        email (str): User's email address
        password (str): User's password
        
    Returns:
        bool: True if credentials are valid, False otherwise
    """
    return DEMO_CREDENTIALS.get(email) == password


@app.post("/api/login", response_model=LoginOut)
async def login(credentials: LoginIn):
    """
    Authenticate user and return authentication token.
    
    Supports Requirements:
    - 1.1: Return authentication token on valid credentials
    - 1.2: Reject login with appropriate error for invalid credentials
    
    Args:
        credentials (LoginIn): User login credentials
        
    Returns:
        LoginOut: Authentication response with token
        
    Raises:
        HTTPException: 401 for invalid credentials, 400 for missing data
    """
    try:
        # Additional validation for empty strings after Pydantic validation
        if not credentials.email or not credentials.email.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is required"
            )
        
        if not credentials.password or not credentials.password.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required"
            )
        
        # Validate credentials
        if not validate_credentials(credentials.email, credentials.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please check your credentials and try again."
            )
        
        # Generate authentication token
        token = generate_demo_token(credentials.email)
        active_tokens.add(token)
        
        return LoginOut(
            token=token,
            message="Login successful"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValidationError as e:
        # Handle Pydantic validation errors
        error_messages = []
        for error in e.errors():
            field = error.get('loc', ['unknown'])[-1]
            message = error.get('msg', 'Invalid input')
            error_messages.append(f"{field}: {message}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(error_messages)
        )
    except Exception as e:
        # Handle unexpected errors
        print(f"Login error: {e}")  # Log for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is temporarily unavailable. Please try again in a moment."
        )


def validate_token(token: str) -> bool:
    """
    Validate authentication token.
    
    Args:
        token (str): Authentication token to validate
        
    Returns:
        bool: True if token is valid, False otherwise
    """
    return token in active_tokens


async def call_openai_api(user_message: str) -> Optional[str]:
    """
    Call OpenAI API to get AI response for healthcare queries.
    
    Args:
        user_message (str): User's healthcare query
        
    Returns:
        Optional[str]: AI response or None if API call fails
        
    Requirements addressed:
        - 5.1: Use GPT-4o-mini model when API key is configured
        - 5.3: Use temperature 0.2 for consistent responses
        - 5.4: Handle API errors gracefully with fallback responses
    """
    if not OPENAI_API_KEY or not HTTPX_AVAILABLE:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT) as client:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "temperature": OPENAI_TEMPERATURE,
                "max_tokens": 500
            }
            
            response = await client.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    ai_response = data["choices"][0]["message"]["content"].strip()
                    
                    # Secondary filtering check - validate AI response for healthcare compliance
                    validated_response = validate_ai_response(ai_response)
                    return validated_response
            elif response.status_code == 401:
                print("OpenAI API authentication failed - invalid API key")
                return None
            elif response.status_code == 429:
                print("OpenAI API rate limit exceeded")
                return None
            elif response.status_code >= 500:
                print(f"OpenAI API server error: {response.status_code}")
                return None
            else:
                print(f"OpenAI API error: {response.status_code}")
                return None
            
    except httpx.TimeoutException:
        print("OpenAI API request timed out")
        return None
    except httpx.ConnectError:
        print("Failed to connect to OpenAI API")
        return None
    except Exception as e:
        print(f"Unexpected error calling OpenAI API: {e}")
        return None


def validate_ai_response(ai_response: str) -> str:
    """
    Validate AI response to ensure it complies with healthcare-only policy.
    
    This function implements the secondary filtering layer that checks if the AI
    model attempted to respond to non-healthcare topics despite the system prompt.
    
    Args:
        ai_response (str): The response from the AI model
        
    Returns:
        str: Either the original AI response if valid, or refusal message if invalid
        
    Requirements addressed:
        - 3.5: Override inappropriate AI responses with refusal message
        - 3.4: Use strict healthcare-focused system prompt
    """
    if not ai_response or not isinstance(ai_response, str):
        return get_refusal_message()
    
    response_lower = ai_response.lower()
    
    # Check if AI is already refusing non-healthcare queries
    refusal_indicators = [
        "sorry, i can only assist with healthcare-related queries",
        "i can only help with healthcare",
        "i'm designed to assist with healthcare",
        "please ask me about health"
    ]
    
    for indicator in refusal_indicators:
        if indicator in response_lower:
            return get_refusal_message()
    
    # Check for signs that AI might be responding to non-healthcare topics
    non_healthcare_indicators = [
        "don't have information about",
        "dont have information about", 
        "can't help with cooking",
        "cant help with cooking",
        "can't help with weather",
        "cant help with weather",
        "can't help with entertainment",
        "cant help with entertainment",
        "can't help with technology",
        "cant help with technology",
        "can't help with travel",
        "cant help with travel",
        "can't help with sports",
        "cant help with sports",
        "can't help with politics",
        "cant help with politics",
        "can't help with finance",
        "cant help with finance",
        "that's not related to healthcare",
        "thats not related to healthcare",
        "that's outside my healthcare expertise",
        "thats outside my healthcare expertise",
        "not a healthcare",
        "not healthcare-related",
        "outside of healthcare",
        "beyond healthcare",
        "unrelated to health",
        "not about health",
        "not medical"
    ]
    
    for indicator in non_healthcare_indicators:
        if indicator in response_lower:
            return get_refusal_message()
    
    # If response passes validation, return original response
    return ai_response


def get_fallback_response(user_message: str) -> str:
    """
    Generate fallback response when OpenAI API is unavailable.
    
    Args:
        user_message (str): User's healthcare query
        
    Returns:
        str: Fallback response for healthcare queries
        
    Requirements addressed:
        - 5.2: Fall back to mock responses when OpenAI API unavailable
        - 5.5: Operate in mock mode without errors when no API key provided
    """
    # Simple keyword-based fallback responses
    message_lower = user_message.lower()
    
    if any(word in message_lower for word in ["symptom", "symptoms", "feel", "pain", "ache", "hurt"]):
        return ("I understand you're asking about symptoms. While I'd love to help with more detailed information, "
                "I'm currently running in limited mode. For any health concerns, please consult with a healthcare "
                "professional who can provide proper evaluation and guidance.")
    
    elif any(word in message_lower for word in ["medication", "medicine", "drug", "prescription"]):
        return ("I see you're asking about medications. For safety reasons and because I'm in limited mode, "
                "please consult with your doctor or pharmacist for accurate information about medications, "
                "dosages, and potential interactions.")
    
    elif any(word in message_lower for word in ["emergency", "urgent", "911", "serious"]):
        return ("If this is a medical emergency, please call 911 or go to your nearest emergency room immediately. "
                "For urgent but non-emergency concerns, contact your healthcare provider or an urgent care center.")
    
    else:
        return ("Thank you for your healthcare question. I'm currently running in limited mode and cannot provide "
                "detailed medical information. Please consult with a qualified healthcare professional for "
                "accurate medical advice and information.")


async def log_chat_interaction(user_message: str, ai_response: str) -> None:
    """
    Log chat interaction with hashed data for privacy protection.
    
    Args:
        user_message (str): User's original message
        ai_response (str): AI's response
        
    Requirements addressed:
        - 4.1: Log hashed versions of queries and responses
        - 4.2: Include timestamps for each interaction
        - 4.4: Never store plain text user queries or responses
    """
    if not DB_AVAILABLE:
        # Database not available, skip logging
        return
        
    try:
        # Hash the messages for privacy protection
        hashed_query = hash_for_logging(user_message, use_hmac=True)
        hashed_response = hash_for_logging(ai_response, use_hmac=True)
        
        # Store in database using proper session management
        db = SessionLocal()
        try:
            chat_log = ChatLog(
                hashed_query=hashed_query,
                hashed_response=hashed_response
            )
            db.add(chat_log)
            db.commit()
        finally:
            db.close()
            
    except Exception as e:
        # Log errors silently - don't break the chat flow
        print(f"Warning: Failed to log chat interaction: {e}")
        pass


@app.post("/api/logout")
async def logout(token: str):
    """
    Logout user and invalidate token.
    
    Args:
        token (str): Authentication token to invalidate
        
    Returns:
        dict: Logout confirmation message
    """
    if token in active_tokens:
        active_tokens.remove(token)
    
    return {"message": "Logout successful"}


@app.post("/api/chat", response_model=ChatOut)
async def chat(chat_request: ChatIn):
    """
    Process chat messages with AI integration and content filtering.
    
    Supports Requirements:
    - 2.1: Display user message in chat interface with timestamp
    - 3.1: Process healthcare-related questions with AI model
    - 3.2: Respond with refusal message for non-healthcare questions
    - 3.3: Use keyword-based filtering as first gate
    - 3.4: Use strict healthcare-focused system prompt
    - 3.5: Override inappropriate AI responses with refusal message
    - 4.1: Log hashed versions of queries and responses
    - 5.1: Use GPT-4o-mini model when API key is configured
    - 5.2: Fall back to mock responses when OpenAI API unavailable
    - 5.3: Use temperature 0.2 for consistent responses
    - 5.4: Handle API errors gracefully with fallback responses
    - 5.5: Operate in mock mode without errors when no API key provided
    
    Args:
        chat_request (ChatIn): Chat message with optional authentication token
        
    Returns:
        ChatOut: AI response to the user query
        
    Raises:
        HTTPException: 401 for invalid token, 400 for invalid input, 500 for server errors
    """
    try:
        # Validate authentication token if provided
        if chat_request.token and not validate_token(chat_request.token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please log in again."
            )
        
        user_message = chat_request.message.strip()
        
        if not user_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please enter a message before sending."
            )
        
        # Check message length
        if len(user_message) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your message is too long. Please keep it under 1000 characters."
            )
        
        # First layer: Keyword-based content filtering
        should_process, refusal_message = should_process_query(user_message)
        
        if not should_process:
            # Log the refusal for monitoring
            await log_chat_interaction(user_message, refusal_message)
            return ChatOut(reply=refusal_message)
        
        # Check if this is a clinic location request
        is_clinic_request, location, clinic_type = detect_clinic_request(user_message)
        
        if is_clinic_request:
            if location == "current_location":
                # Handle "near me" requests - ask for location
                location_request_response = (
                    "I'd be happy to help you find nearby healthcare facilities! 🏥\n\n"
                    "However, I need to know your location to provide accurate results. "
                    "Could you please tell me your city, zip code, or general area?\n\n"
                    "**Examples:**\n"
                    "• 'Find hospitals in Chicago'\n"
                    "• 'Show me clinics in 90210'\n"
                    "• 'I need a doctor in New York, NY'\n"
                    "• 'Find pharmacies in Los Angeles'\n\n"
                    "The more specific you are with the location, the better results I can provide!"
                )
                await log_chat_interaction(user_message, location_request_response)
                return ChatOut(reply=location_request_response)
            
            elif location:
                # Handle clinic location request with specific location
                print(f"🔍 Processing clinic request for {clinic_type} in {location}")
                clinics = await search_clinics_by_location(location, clinic_type)
                
                # Always return a clinic response, even if no results found
                clinic_response = format_clinic_response(clinics, location, clinic_type)
                await log_chat_interaction(user_message, clinic_response)
                return ChatOut(reply=clinic_response)
            
            else:
                # Clinic request detected but no location found
                no_location_response = (
                    f"I understand you're looking for {clinic_type}s! 🏥\n\n"
                    "To help you find the best options, I need to know where you're located. "
                    "Please include a location in your request.\n\n"
                    "**Try asking like this:**\n"
                    f"• 'Find {clinic_type}s in [your city]'\n"
                    f"• 'Show me {clinic_type}s near [zip code]'\n"
                    f"• 'I need a {clinic_type} in [city, state]'\n\n"
                    "What location would you like me to search?"
                )
                await log_chat_interaction(user_message, no_location_response)
                return ChatOut(reply=no_location_response)
        
        # Only process non-clinic requests with AI
        ai_response = await call_openai_api(user_message)
        
        if ai_response is None:
            # Fallback when OpenAI API is unavailable
            ai_response = get_fallback_response(user_message)
        
        # Ensure we have a valid response
        if not ai_response or not ai_response.strip():
            ai_response = ("I apologize, but I'm having trouble generating a response right now. "
                          "Please try rephrasing your question or try again in a moment.")
        
        # Log the interaction with hashed data (gracefully handle logging errors)
        try:
            await log_chat_interaction(user_message, ai_response)
        except Exception as log_error:
            # Don't fail the entire request if logging fails
            print(f"Warning: Chat logging failed: {log_error}")
        
        return ChatOut(reply=ai_response)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValidationError as e:
        # Handle Pydantic validation errors
        error_messages = []
        for error in e.errors():
            field = error.get('loc', ['unknown'])[-1]
            message = error.get('msg', 'Invalid input')
            error_messages.append(f"{field}: {message}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(error_messages)
        )
    except Exception as e:
        # Handle unexpected errors
        print(f"Chat error: {e}")  # Log for debugging
        
        # Provide a helpful error message based on the type of error
        if "database" in str(e).lower():
            error_message = "I'm having trouble saving our conversation. Your message was processed, but it may not be logged."
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            error_message = "I'm having network connectivity issues. Please check your connection and try again."
        else:
            error_message = "I encountered an unexpected error. Please try again in a moment."
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )


# Root endpoint to serve main HTML interface
@app.get("/")
async def root():
    """
    Serve the main HTML interface.
    
    Requirements addressed:
    - 7.3: Serve static files and API endpoints correctly
    - 6.1: Display modern, healthcare-themed UI
    
    Returns:
        FileResponse: Main HTML interface file
    """
    return FileResponse("app/static/index.html")


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        dict: Application health status
    """
    return {
        "status": "healthy",
        "service": "healthcare-chatbot-mvp",
        "authentication": "enabled"
    }