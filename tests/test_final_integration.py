"""
Final integration and system testing for Healthcare Chatbot MVP.

This test suite implements Task 17: Final integration and system testing
- Test complete end-to-end user journey from login to chat
- Verify content filtering works with various query types
- Test fallback mechanisms when OpenAI API is unavailable
- Validate responsive design across different devices and browsers
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os
import time
import json
from typing import Dict, List

from app.main import app, active_tokens
from app.content_filter import REFUSAL_MESSAGE, is_health_related
from app.security import sha256_hex, hmac256_hex, hash_for_logging
from app.models import LoginIn, LoginOut, ChatIn, ChatOut


class TestEndToEndUserJourney:
    """Test complete end-to-end user journey from login to chat."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        active_tokens.clear()
        
        # Set up test database
        self.test_db_path = tempfile.mktemp(suffix='.db')
        self.test_db_url = f"sqlite:///{self.test_db_path}"
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db import Base
        
        self.test_engine = create_engine(
            self.test_db_url,
            connect_args={"check_same_thread": False}
        )
        self.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        
        Base.metadata.create_all(bind=self.test_engine)
        
        # Patch SessionLocal for testing
        self.session_patcher = patch('app.main.SessionLocal', self.TestSessionLocal)
        self.session_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
        self.session_patcher.stop()
        
        if hasattr(self, 'test_engine'):
            self.test_engine.dispose()
        
        if os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except PermissionError:
                pass
    
    def test_complete_user_journey_with_demo_credentials(self):
        """Test Requirements 1.1-1.5, 2.1-2.5: Complete user journey with demo credentials."""
        # Step 1: User accesses the application
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        
        # Step 2: User attempts to use demo credentials (Requirement 1.3)
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "token" in login_data
        assert "Login successful" in login_data["message"]
        token = login_data["token"]
        
        # Verify token is active (Requirement 1.1)
        assert token in active_tokens
        
        # Step 3: User starts chatting with healthcare questions (Requirements 2.1-2.5)
        healthcare_conversation = [
            {
                "message": "I have been feeling unwell with symptoms lately",
                "expected_response_type": "healthcare_advice"
            },
            {
                "message": "I have a headache and feel tired",
                "expected_response_type": "healthcare_advice"
            },
            {
                "message": "Should I be concerned about these health symptoms?",
                "expected_response_type": "healthcare_advice"
            },
            {
                "message": "What medical advice can help me feel better?",
                "expected_response_type": "healthcare_advice"
            }
        ]
        
        for exchange in healthcare_conversation:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare advice for: {exchange['message']}"
                
                chat_response = self.client.post("/api/chat", json={
                    "message": exchange["message"],
                    "token": token
                })
                
                assert chat_response.status_code == 200
                chat_data = chat_response.json()
                assert "reply" in chat_data
                assert chat_data["reply"] != REFUSAL_MESSAGE
                assert "Healthcare advice" in chat_data["reply"]
        
        # Step 4: User tries non-healthcare questions (should be refused)
        non_healthcare_queries = [
            "What's the weather today?",
            "How do I cook pasta?",
            "Tell me a joke",
            "What's the capital of France?"
        ]
        
        for query in non_healthcare_queries:
            chat_response = self.client.post("/api/chat", json={
                "message": query,
                "token": token
            })
            
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            assert chat_data["reply"] == REFUSAL_MESSAGE
        
        # Step 5: User logs out (Requirement 1.5)
        logout_response = self.client.post(f"/api/logout?token={token}")
        assert logout_response.status_code == 200
        assert logout_response.json()["message"] == "Logout successful"
        
        # Verify token is invalidated
        assert token not in active_tokens
        
        # Step 6: Verify user cannot chat after logout
        chat_response = self.client.post("/api/chat", json={
            "message": "I have a fever",
            "token": token
        })
        
        assert chat_response.status_code == 401
        assert "session has expired" in chat_response.json()["detail"]
    
    def test_complete_user_journey_with_regular_credentials(self):
        """Test complete user journey with regular user credentials."""
        # Step 1: User logs in with regular credentials
        login_response = self.client.post("/api/login", json={
            "email": "user@example.com",
            "password": "password123"
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        
        # Step 2: User engages in healthcare conversation
        healthcare_scenarios = [
            {
                "query": "I've been having chest pain",
                "ai_response": "Chest pain can be serious. Please seek immediate medical attention if you're experiencing severe chest pain.",
                "should_contain": ["medical attention", "serious"]
            },
            {
                "query": "What are the symptoms of diabetes?",
                "ai_response": "Common diabetes symptoms include increased thirst, frequent urination, unexplained weight loss, and fatigue.",
                "should_contain": ["thirst", "urination", "symptoms"]
            },
            {
                "query": "How can I manage high blood pressure?",
                "ai_response": "Blood pressure management typically involves lifestyle changes like diet, exercise, and medication as prescribed by your doctor.",
                "should_contain": ["lifestyle", "diet", "exercise"]
            }
        ]
        
        for scenario in healthcare_scenarios:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = scenario["ai_response"]
                
                chat_response = self.client.post("/api/chat", json={
                    "message": scenario["query"],
                    "token": token
                })
                
                assert chat_response.status_code == 200
                chat_data = chat_response.json()
                assert chat_data["reply"] == scenario["ai_response"]
                
                # Verify response contains expected healthcare content
                response_lower = chat_data["reply"].lower()
                assert any(keyword in response_lower for keyword in scenario["should_contain"])
        
        # Step 3: User session remains active throughout conversation
        # Test session persistence with multiple rapid requests
        for i in range(5):
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare response #{i+1}"
                
                chat_response = self.client.post("/api/chat", json={
                    "message": f"Healthcare question #{i+1}",
                    "token": token
                })
                
                assert chat_response.status_code == 200
                assert token in active_tokens  # Token should remain valid
    
    def test_user_journey_with_authentication_errors(self):
        """Test user journey with authentication error recovery."""
        # Step 1: User tries wrong credentials
        wrong_login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "wrongpassword"
        })
        
        assert wrong_login_response.status_code == 401
        assert "Invalid email or password" in wrong_login_response.json()["detail"]
        
        # Step 2: User tries with missing email
        missing_email_response = self.client.post("/api/login", json={
            "email": "",
            "password": "demo123"
        })
        
        assert missing_email_response.status_code == 400
        assert "required" in missing_email_response.json()["detail"].lower()
        
        # Step 3: User corrects credentials and succeeds
        correct_login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert correct_login_response.status_code == 200
        token = correct_login_response.json()["token"]
        
        # Step 4: User can now chat successfully
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice after successful login"
            
            chat_response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": token
            })
            
            assert chat_response.status_code == 200
            assert "Healthcare advice" in chat_response.json()["reply"]


class TestContentFilteringVariousQueryTypes:
    """Verify content filtering works with various query types."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        active_tokens.clear()
        
        # Get valid token for testing
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        self.token = login_response.json()["token"]
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
    
    def test_healthcare_query_variations(self):
        """Test Requirements 3.1-3.5: Various healthcare query types are processed correctly."""
        healthcare_query_types = [
            # Symptom-based queries
            {
                "category": "symptoms",
                "queries": [
                    "I have a headache",
                    "My stomach hurts",
                    "I feel dizzy and nauseous",
                    "I've been coughing for days",
                    "I have chest pain"
                ]
            },
            # Medical condition queries
            {
                "category": "conditions",
                "queries": [
                    "What is diabetes?",
                    "Tell me about hypertension",
                    "What are the signs of depression?",
                    "How is asthma treated?",
                    "What causes migraines?"
                ]
            },
            # Medication queries
            {
                "category": "medications",
                "queries": [
                    "What medications help with pain?",
                    "Are there side effects to aspirin?",
                    "How does insulin work?",
                    "What is the dosage for ibuprofen?",
                    "Can I take these medications together?"
                ]
            },
            # Prevention and wellness queries
            {
                "category": "prevention",
                "queries": [
                    "How can I prevent heart disease?",
                    "What vaccines do I need?",
                    "How often should I exercise?",
                    "What foods are good for my health?",
                    "How much sleep do I need?"
                ]
            },
            # Emergency and urgent queries
            {
                "category": "emergency",
                "queries": [
                    "I think I'm having a heart attack",
                    "I can't breathe properly",
                    "I have severe chest pain",
                    "I'm bleeding heavily",
                    "I feel like I'm going to faint"
                ]
            }
        ]
        
        for category_data in healthcare_query_types:
            category = category_data["category"]
            queries = category_data["queries"]
            
            for query in queries:
                with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                    mock_openai.return_value = f"Healthcare advice for {category}: {query}"
                    
                    response = self.client.post("/api/chat", json={
                        "message": query,
                        "token": self.token
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["reply"] != REFUSAL_MESSAGE, f"Healthcare query '{query}' was incorrectly refused"
                    assert "Healthcare advice" in data["reply"]
                    mock_openai.assert_called_once_with(query)
    
    def test_non_healthcare_query_variations(self):
        """Test various non-healthcare query types are correctly refused."""
        non_healthcare_query_types = [
            # Entertainment queries
            {
                "category": "entertainment",
                "queries": [
                    "Tell me a joke",
                    "What movies should I watch?",
                    "Who won the game last night?",
                    "What's on TV tonight?",
                    "Recommend some music"
                ]
            },
            # Technology queries
            {
                "category": "technology",
                "queries": [
                    "How do I fix my computer?",
                    "What's the best smartphone?",
                    "How do I code in Python?",
                    "What is artificial intelligence?",
                    "How does the internet work?"
                ]
            },
            # Cooking and food queries (non-health related)
            {
                "category": "cooking",
                "queries": [
                    "How do I cook pasta?",
                    "What's a good recipe for cake?",
                    "How long do I bake cookies?",
                    "What spices go with chicken?",
                    "How do I make pizza dough?"
                ]
            },
            # Weather and travel queries
            {
                "category": "weather_travel",
                "queries": [
                    "What's the weather today?",
                    "Will it rain tomorrow?",
                    "What's the best time to visit Paris?",
                    "How do I book a flight?",
                    "What's the temperature outside?"
                ]
            },
            # General knowledge queries
            {
                "category": "general_knowledge",
                "queries": [
                    "What's the capital of France?",
                    "Who was the first president?",
                    "What year did World War II end?",
                    "How many planets are there?",
                    "What's the largest ocean?"
                ]
            }
        ]
        
        for category_data in non_healthcare_query_types:
            category = category_data["category"]
            queries = category_data["queries"]
            
            for query in queries:
                # Non-healthcare queries should not reach OpenAI
                response = self.client.post("/api/chat", json={
                    "message": query,
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == REFUSAL_MESSAGE, f"Non-healthcare query '{query}' was not refused"
    
    def test_mixed_content_queries(self):
        """Test queries that mix healthcare and non-healthcare content."""
        mixed_queries = [
            {
                "query": "I have a headache, also what's the weather?",
                "should_process": True,
                "reason": "Contains healthcare keyword 'headache'"
            },
            {
                "query": "What's the weather? I also have a fever.",
                "should_process": True,
                "reason": "Contains healthcare keyword 'fever'"
            },
            {
                "query": "Tell me about diabetes and also recommend a movie",
                "should_process": True,
                "reason": "Contains healthcare keyword 'diabetes'"
            },
            {
                "query": "How to cook pasta and what's the capital of France?",
                "should_process": False,
                "reason": "No healthcare keywords present"
            },
            {
                "query": "I need entertainment and also want to know about sports",
                "should_process": False,
                "reason": "No healthcare keywords present"
            }
        ]
        
        for test_case in mixed_queries:
            if test_case["should_process"]:
                with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                    mock_openai.return_value = f"Healthcare response for: {test_case['query']}"
                    
                    response = self.client.post("/api/chat", json={
                        "message": test_case["query"],
                        "token": self.token
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["reply"] != REFUSAL_MESSAGE, f"Mixed query should be processed: {test_case['reason']}"
                    mock_openai.assert_called_once()
            else:
                response = self.client.post("/api/chat", json={
                    "message": test_case["query"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == REFUSAL_MESSAGE, f"Mixed query should be refused: {test_case['reason']}"
    
    def test_edge_case_queries(self):
        """Test edge case queries for content filtering."""
        edge_cases = [
            {
                "query": "health",  # Single word
                "should_process": True
            },
            {
                "query": "HEALTH QUESTION",  # All caps
                "should_process": True
            },
            {
                "query": "I'm asking about my health condition",  # Formal language
                "should_process": True
            },
            {
                "query": "medical advice needed",  # Brief request
                "should_process": True
            },
            {
                "query": "entertainment",  # Single non-healthcare word
                "should_process": False
            },
            {
                "query": "COOKING RECIPE",  # All caps non-healthcare
                "should_process": False
            },
            {
                "query": "I want to know about technology trends",  # Formal non-healthcare
                "should_process": False
            }
        ]
        
        for test_case in edge_cases:
            if test_case["should_process"]:
                with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                    mock_openai.return_value = f"Healthcare response for: {test_case['query']}"
                    
                    response = self.client.post("/api/chat", json={
                        "message": test_case["query"],
                        "token": self.token
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["reply"] != REFUSAL_MESSAGE
            else:
                response = self.client.post("/api/chat", json={
                    "message": test_case["query"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == REFUSAL_MESSAGE


class TestFallbackMechanisms:
    """Test fallback mechanisms when OpenAI API is unavailable."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        active_tokens.clear()
        
        # Get valid token for testing
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        self.token = login_response.json()["token"]
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
    
    def test_api_unavailable_fallback(self):
        """Test Requirements 5.2, 5.4, 5.5: Fallback when OpenAI API is unavailable."""
        healthcare_queries = [
            "I have a headache and pain",
            "What are flu symptoms and illness signs?",
            "I feel tired and weak with fatigue",
            "My blood pressure is high, health concern",
            "I need medication advice for my condition"
        ]
        
        for query in healthcare_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = None  # Simulate API unavailable
                
                response = self.client.post("/api/chat", json={
                    "message": query,
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] != REFUSAL_MESSAGE
                assert "limited mode" in data["reply"] or "consult" in data["reply"]
                assert len(data["reply"]) > 0
    
    def test_api_timeout_fallback(self):
        """Test fallback when OpenAI API times out."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None  # Simulate API failure/timeout
            
            response = self.client.post("/api/chat", json={
                "message": "I have chest pain and symptoms",
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] != REFUSAL_MESSAGE
            assert len(data["reply"]) > 0
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
    
    def test_api_error_recovery(self):
        """Test system recovery after API errors."""
        # Step 1: API fails
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None
            
            response = self.client.post("/api/chat", json={
                "message": "I have a fever",
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
        
        # Step 2: API recovers
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice: Rest and drink fluids for fever"
            
            response = self.client.post("/api/chat", json={
                "message": "What should I do for fever?",
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "Healthcare advice" in data["reply"]
            assert "Rest and drink fluids" in data["reply"]
    
    def test_no_api_key_mock_mode(self):
        """Test operation in mock mode when no API key is provided."""
        with patch.dict('os.environ', {}, clear=True):  # Remove API key
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = None  # No API key available
                
                response = self.client.post("/api/chat", json={
                    "message": "I have a headache",
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] != REFUSAL_MESSAGE
                assert len(data["reply"]) > 0
                assert "limited mode" in data["reply"] or "consult" in data["reply"]
    
    def test_fallback_response_quality(self):
        """Test that fallback responses are appropriate for different query types."""
        fallback_scenarios = [
            {
                "query": "I have symptoms like headache and fatigue",
                "expected_keywords": ["symptoms", "consult", "healthcare", "professional"]
            },
            {
                "query": "What medications can help with pain?",
                "expected_keywords": ["medication", "doctor", "pharmacist", "consult"]
            },
            {
                "query": "I think this might be an emergency",
                "expected_keywords": ["emergency", "911", "immediate", "urgent"]
            },
            {
                "query": "I need general health advice",
                "expected_keywords": ["limited mode", "consult", "healthcare", "professional"]
            }
        ]
        
        for scenario in fallback_scenarios:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = None  # Force fallback
                
                response = self.client.post("/api/chat", json={
                    "message": scenario["query"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                
                # Check that fallback response contains appropriate keywords
                response_lower = data["reply"].lower()
                assert any(keyword in response_lower for keyword in scenario["expected_keywords"])


class TestResponsiveDesignValidation:
    """Validate responsive design across different devices and browsers."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
    
    def test_html_structure_and_responsiveness(self):
        """Test Requirements 6.1-6.5: HTML structure supports responsive design."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        
        # Read the HTML content to verify responsive design elements
        html_content = response.content.decode('utf-8')
        
        # Check for Bootstrap (responsive framework)
        assert "bootstrap" in html_content.lower()
        
        # Check for viewport meta tag (essential for mobile responsiveness)
        assert "viewport" in html_content.lower()
        assert "width=device-width" in html_content.lower()
        
        # Check for responsive CSS classes
        responsive_indicators = [
            "container",
            "row",
            "col-",
            "d-none",
            "d-block",
            "d-sm-",
            "d-md-",
            "d-lg-"
        ]
        
        found_responsive_classes = []
        for indicator in responsive_indicators:
            if indicator in html_content:
                found_responsive_classes.append(indicator)
        
        # Should have at least some responsive classes
        assert len(found_responsive_classes) > 0, "No responsive CSS classes found"
    
    def test_mobile_friendly_form_elements(self):
        """Test that form elements are mobile-friendly."""
        response = self.client.get("/")
        html_content = response.content.decode('utf-8')
        
        # Check for mobile-friendly input types
        mobile_friendly_elements = [
            'type="email"',  # Brings up email keyboard on mobile
            'type="password"',  # Secure password input
            'type="text"',  # Standard text input
            'class="form-control"',  # Bootstrap form styling
            'class="btn"'  # Bootstrap button styling
        ]
        
        found_elements = []
        for element in mobile_friendly_elements:
            if element in html_content:
                found_elements.append(element)
        
        assert len(found_elements) >= 3, "Not enough mobile-friendly form elements found"
    
    def test_healthcare_themed_styling(self):
        """Test Requirements 6.1, 6.4: Healthcare-themed UI and iconography."""
        response = self.client.get("/")
        html_content = response.content.decode('utf-8')
        
        # Check for healthcare-related styling and content
        healthcare_indicators = [
            "healthcare",
            "medical",
            "health",
            "chatbot",
            "assistant",
            "blue",  # Common healthcare color
            "icon",
            "fa-",  # Font Awesome icons
            "bi-"   # Bootstrap icons
        ]
        
        found_indicators = []
        for indicator in healthcare_indicators:
            if indicator.lower() in html_content.lower():
                found_indicators.append(indicator)
        
        assert len(found_indicators) >= 3, "Not enough healthcare-themed elements found"
    
    def test_accessibility_features(self):
        """Test that the interface includes accessibility features."""
        response = self.client.get("/")
        html_content = response.content.decode('utf-8')
        
        # Check for accessibility features
        accessibility_features = [
            'aria-',  # ARIA attributes
            'role=',  # ARIA roles
            'alt=',   # Alt text for images
            'label',  # Form labels
            'title=', # Title attributes
            'tabindex'  # Tab navigation
        ]
        
        found_features = []
        for feature in accessibility_features:
            if feature in html_content:
                found_features.append(feature)
        
        # Should have at least some accessibility features
        assert len(found_features) > 0, "No accessibility features found"
    
    def test_cross_browser_compatibility_headers(self):
        """Test that appropriate headers are set for cross-browser compatibility."""
        response = self.client.get("/")
        
        # Check that content type is properly set
        assert "text/html" in response.headers.get("content-type", "")
        
        # Check that the response is not empty
        assert len(response.content) > 0
        
        # Verify HTML5 doctype for modern browser compatibility
        html_content = response.content.decode('utf-8')
        assert "<!DOCTYPE html>" in html_content or "<!doctype html>" in html_content.lower()


class TestSystemIntegrationAndResilience:
    """Test overall system integration and resilience."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        active_tokens.clear()
        
        # Set up test database
        self.test_db_path = tempfile.mktemp(suffix='.db')
        self.test_db_url = f"sqlite:///{self.test_db_path}"
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db import Base
        
        self.test_engine = create_engine(
            self.test_db_url,
            connect_args={"check_same_thread": False}
        )
        self.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        
        Base.metadata.create_all(bind=self.test_engine)
        
        # Patch SessionLocal for testing
        self.session_patcher = patch('app.main.SessionLocal', self.TestSessionLocal)
        self.session_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
        self.session_patcher.stop()
        
        if hasattr(self, 'test_engine'):
            self.test_engine.dispose()
        
        if os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except PermissionError:
                pass
    
    def test_concurrent_user_sessions(self):
        """Test system handles multiple concurrent users correctly."""
        # Create multiple user sessions
        users = [
            {"email": "demo@healthcare.com", "password": "demo123"},
            {"email": "user@example.com", "password": "password123"}
        ]
        
        user_tokens = []
        
        # All users log in
        for user in users:
            response = self.client.post("/api/login", json=user)
            assert response.status_code == 200
            user_tokens.append(response.json()["token"])
        
        # Users chat simultaneously
        for i, token in enumerate(user_tokens):
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare advice for user {i+1}"
                
                response = self.client.post("/api/chat", json={
                    "message": f"I have a health question from user {i+1}",
                    "token": token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert f"user {i+1}" in data["reply"]
        
        # Verify all tokens are still active
        for token in user_tokens:
            assert token in active_tokens
    
    def test_system_health_and_monitoring(self):
        """Test system health check and monitoring endpoints."""
        # Test health check endpoint
        health_response = self.client.get("/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert "service" in health_data
        assert "authentication" in health_data
    
    def test_error_handling_and_recovery(self):
        """Test comprehensive error handling and recovery."""
        # Get valid token
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        # Test various error scenarios
        error_scenarios = [
            {
                "name": "empty_message",
                "request": {"message": "", "token": token},
                "expected_status": 400,
                "expected_error": "message cannot be empty"
            },
            {
                "name": "too_long_message",
                "request": {"message": "x" * 1001, "token": token},
                "expected_status": 400,
                "expected_error": "too long"
            },
            {
                "name": "invalid_token",
                "request": {"message": "I have a headache", "token": "invalid_token"},
                "expected_status": 401,
                "expected_error": "session has expired"
            }
        ]
        
        for scenario in error_scenarios:
            response = self.client.post("/api/chat", json=scenario["request"])
            assert response.status_code == scenario["expected_status"]
            assert scenario["expected_error"] in response.json()["detail"].lower()
        
        # Verify system recovers and works normally after errors
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "System recovered successfully"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": token
            })
            
            assert response.status_code == 200
            assert "System recovered" in response.json()["reply"]
    
    def test_database_logging_integration(self):
        """Test that database logging works correctly with the chat system."""
        # Get valid token
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        # Send healthcare message
        user_message = "I have been experiencing headaches"
        ai_response = "Healthcare advice for headaches"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = ai_response
            
            response = self.client.post("/api/chat", json={
                "message": user_message,
                "token": token
            })
            
            assert response.status_code == 200
        
        # Verify logging occurred
        from app.db import ChatLog
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).all()
            assert len(logs) >= 1
            
            log_entry = logs[-1]
            assert len(log_entry.hashed_query) == 64  # SHA256 hex length
            assert len(log_entry.hashed_response) == 64
            assert log_entry.hashed_query != user_message  # Should be hashed
            assert log_entry.hashed_response != ai_response  # Should be hashed
            assert log_entry.timestamp is not None
            
        finally:
            db.close()
    
    def test_complete_system_integration(self):
        """Test complete system integration across all components."""
        # Step 1: User accesses application
        root_response = self.client.get("/")
        assert root_response.status_code == 200
        
        # Step 2: User logs in
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        
        # Step 3: User chats with healthcare questions (tests content filtering)
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice for your symptoms"
            
            chat_response = self.client.post("/api/chat", json={
                "message": "I have been feeling unwell with flu-like symptoms",
                "token": token
            })
            
            assert chat_response.status_code == 200
            assert "Healthcare advice" in chat_response.json()["reply"]
        
        # Step 4: User tries non-healthcare question (tests filtering)
        non_healthcare_response = self.client.post("/api/chat", json={
            "message": "What's the weather today?",
            "token": token
        })
        
        assert non_healthcare_response.status_code == 200
        assert non_healthcare_response.json()["reply"] == REFUSAL_MESSAGE
        
        # Step 5: Test API fallback
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None  # API unavailable
            
            fallback_response = self.client.post("/api/chat", json={
                "message": "I need medical advice",
                "token": token
            })
            
            assert fallback_response.status_code == 200
            assert "limited mode" in fallback_response.json()["reply"] or "consult" in fallback_response.json()["reply"]
        
        # Step 6: User logs out
        logout_response = self.client.post(f"/api/logout?token={token}")
        assert logout_response.status_code == 200
        
        # Step 7: Verify system health
        health_response = self.client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])