"""
Integration tests for complete user flows.

Tests end-to-end scenarios that span multiple components and simulate
real user interactions with the Healthcare Chatbot MVP.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os
import time

from app.main import app, active_tokens
from app.content_filter import REFUSAL_MESSAGE
from app.db import ChatLog


class TestCompleteUserFlows:
    """Test complete user interaction flows."""
    
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
    
    def test_new_user_complete_journey(self):
        """Test complete journey for a new user."""
        # Step 1: User attempts to chat without authentication
        response = self.client.post("/api/chat", json={
            "message": "I have a headache, what should I do?"
        })
        
        # Should work without token (demo mode)
        assert response.status_code == 200
        
        # Step 2: User decides to login
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        token = login_data["token"]
        assert "Login successful" in login_data["message"]
        
        # Step 3: User chats with healthcare questions
        healthcare_questions = [
            "What are the symptoms of flu?",
            "How can I treat a fever?",
            "When should I see a doctor for chest pain?",
            "What medications help with headaches?"
        ]
        
        for question in healthcare_questions:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare advice for: {question}"
                
                response = self.client.post("/api/chat", json={
                    "message": question,
                    "token": token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] != REFUSAL_MESSAGE
                assert "Healthcare advice" in data["reply"]
        
        # Step 4: User tries non-healthcare questions
        non_healthcare_questions = [
            "What's the weather today?",
            "How do I cook pasta?",
            "Tell me a joke"
        ]
        
        for question in non_healthcare_questions:
            response = self.client.post("/api/chat", json={
                "message": question,
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] == REFUSAL_MESSAGE
        
        # Step 5: User logs out
        logout_response = self.client.post(f"/api/logout?token={token}")
        
        assert logout_response.status_code == 200
        logout_data = logout_response.json()
        assert logout_data["message"] == "Logout successful"
        
        # Step 6: Verify token is invalidated
        response = self.client.post("/api/chat", json={
            "message": "I have a fever",
            "token": token
        })
        
        assert response.status_code == 401
        assert "session has expired" in response.json()["detail"]
    
    def test_returning_user_flow(self):
        """Test flow for a returning user."""
        # Step 1: User logs in with known credentials
        login_response = self.client.post("/api/login", json={
            "email": "user@example.com",
            "password": "password123"
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        
        # Step 2: User immediately starts chatting (familiar with system)
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Based on your symptoms, you should rest and stay hydrated."
            
            response = self.client.post("/api/chat", json={
                "message": "I'm feeling under the weather with a runny nose and mild cough",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "rest and stay hydrated" in data["reply"]
        
        # Step 3: User asks follow-up questions
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Over-the-counter medications like acetaminophen can help."
            
            response = self.client.post("/api/chat", json={
                "message": "What over-the-counter medications would help?",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "acetaminophen" in data["reply"]
        
        # Step 4: User continues session without logging out (session persistence)
        time.sleep(0.1)  # Small delay to simulate time passing
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "If symptoms persist for more than a week, consult a doctor."
            
            response = self.client.post("/api/chat", json={
                "message": "How long should I wait before seeing a doctor?",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "consult a doctor" in data["reply"]
    
    def test_error_recovery_flow(self):
        """Test user flow with error recovery scenarios."""
        # Step 1: User tries to login with wrong credentials
        wrong_login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "wrongpassword"
        })
        
        assert wrong_login_response.status_code == 401
        assert "Invalid email or password" in wrong_login_response.json()["detail"]
        
        # Step 2: User corrects credentials and logs in successfully
        correct_login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert correct_login_response.status_code == 200
        token = correct_login_response.json()["token"]
        
        # Step 3: User chats normally
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": token
            })
            
            assert response.status_code == 200
        
        # Step 4: Simulate OpenAI API failure
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None  # API failure
            
            response = self.client.post("/api/chat", json={
                "message": "What should I do for a fever?",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
        
        # Step 5: API recovers, user continues normally
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "For fever, rest and drink plenty of fluids."
            
            response = self.client.post("/api/chat", json={
                "message": "Any other advice for fever?",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "rest and drink plenty of fluids" in data["reply"]
    
    def test_multiple_concurrent_users_flow(self):
        """Test multiple users using the system concurrently."""
        # Create multiple user sessions
        users = [
            {"email": "demo@healthcare.com", "password": "demo123", "name": "Demo User"},
            {"email": "user@example.com", "password": "password123", "name": "Regular User"}
        ]
        
        user_tokens = {}
        
        # Step 1: All users log in
        for user in users:
            response = self.client.post("/api/login", json={
                "email": user["email"],
                "password": user["password"]
            })
            
            assert response.status_code == 200
            user_tokens[user["name"]] = response.json()["token"]
        
        # Step 2: Users chat simultaneously with different queries
        user_queries = {
            "Demo User": [
                "I have a headache",
                "What are flu symptoms?",
                "How to treat a fever?"
            ],
            "Regular User": [
                "My blood pressure is high",
                "I need medication advice",
                "When should I see a doctor?"
            ]
        }
        
        # Simulate concurrent requests
        for user_name, queries in user_queries.items():
            token = user_tokens[user_name]
            
            for query in queries:
                with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                    mock_openai.return_value = f"Healthcare advice for {user_name}: {query}"
                    
                    response = self.client.post("/api/chat", json={
                        "message": query,
                        "token": token
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert user_name in data["reply"]
        
        # Step 3: One user logs out, others continue
        logout_response = self.client.post(f"/api/logout?token={user_tokens['Demo User']}")
        assert logout_response.status_code == 200
        
        # Remaining user should still work
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Continued healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have more questions",
                "token": user_tokens["Regular User"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "Continued healthcare advice" in data["reply"]
        
        # Logged out user should be rejected
        response = self.client.post("/api/chat", json={
            "message": "I have questions too",
            "token": user_tokens["Demo User"]
        })
        
        assert response.status_code == 401
    
    def test_edge_case_user_behavior_flow(self):
        """Test user flow with edge case behaviors."""
        # Step 1: User logs in
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        token = login_response.json()["token"]
        
        # Step 2: User sends empty messages
        response = self.client.post("/api/chat", json={
            "message": "",
            "token": token
        })
        
        assert response.status_code == 400
        assert "enter a message" in response.json()["detail"]
        
        # Step 3: User sends very long message
        long_message = "I have symptoms including " + "pain, " * 200  # Over 1000 chars
        
        response = self.client.post("/api/chat", json={
            "message": long_message,
            "token": token
        })
        
        assert response.status_code == 400
        assert "too long" in response.json()["detail"]
        
        # Step 4: User sends malicious content
        response = self.client.post("/api/chat", json={
            "message": "<script>alert('xss')</script>I have a headache",
            "token": token
        })
        
        assert response.status_code == 400
        assert "invalid content" in response.json()["detail"]
        
        # Step 5: User sends valid message after errors
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice for your headache"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache, what should I do?",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "Healthcare advice" in data["reply"]
    
    def test_system_resilience_flow(self):
        """Test system resilience under various failure conditions."""
        # Step 1: User logs in normally
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        token = login_response.json()["token"]
        
        # Step 2: Chat with database logging failure
        with patch('app.main.log_chat_interaction', new_callable=AsyncMock) as mock_log:
            mock_log.side_effect = Exception("Database connection error")
            
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = "Healthcare advice despite logging error"
                
                response = self.client.post("/api/chat", json={
                    "message": "I have a fever",
                    "token": token
                })
                
                # Should still work despite logging failure
                assert response.status_code == 200
                data = response.json()
                assert "Healthcare advice" in data["reply"]
        
        # Step 3: Chat with OpenAI API timeout
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.side_effect = Exception("API timeout")
            
            response = self.client.post("/api/chat", json={
                "message": "What are cold symptoms?",
                "token": token
            })
            
            # Should fallback gracefully
            assert response.status_code == 200
            data = response.json()
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
        
        # Step 4: System recovers, normal operation resumes
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "System is back to normal operation"
            
            response = self.client.post("/api/chat", json={
                "message": "How are you working now?",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "normal operation" in data["reply"]


class TestHealthcareSpecificFlows:
    """Test flows specific to healthcare scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        active_tokens.clear()
        
        # Login and get token for tests
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        self.token = login_response.json()["token"]
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
    
    def test_symptom_assessment_flow(self):
        """Test flow for symptom assessment conversation."""
        conversation_flow = [
            {
                "user": "I've been feeling unwell lately",
                "ai": "I understand you're not feeling well. Can you describe your specific symptoms?"
            },
            {
                "user": "I have a headache and feel tired",
                "ai": "Headaches and fatigue can have various causes. How long have you been experiencing these symptoms?"
            },
            {
                "user": "About 3 days now",
                "ai": "For symptoms lasting 3 days, it's important to rest and stay hydrated. If symptoms worsen or persist beyond a week, consider consulting a healthcare provider."
            },
            {
                "user": "Should I take any medication?",
                "ai": "For headaches, over-the-counter pain relievers like acetaminophen or ibuprofen may help. However, please consult with a pharmacist or doctor for personalized advice."
            }
        ]
        
        for exchange in conversation_flow:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = exchange["ai"]
                
                response = self.client.post("/api/chat", json={
                    "message": exchange["user"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == exchange["ai"]
    
    def test_emergency_scenario_flow(self):
        """Test flow for emergency scenarios."""
        emergency_queries = [
            {
                "query": "I'm having severe chest pain",
                "expected_keywords": ["emergency", "911", "immediate", "urgent"]
            },
            {
                "query": "I can't breathe properly",
                "expected_keywords": ["emergency", "911", "immediate", "urgent"]
            },
            {
                "query": "I think I'm having a heart attack",
                "expected_keywords": ["emergency", "911", "immediate", "urgent"]
            }
        ]
        
        for scenario in emergency_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = "If this is a medical emergency, please call 911 immediately or go to the nearest emergency room."
                
                response = self.client.post("/api/chat", json={
                    "message": scenario["query"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                
                # Should contain emergency guidance
                reply_lower = data["reply"].lower()
                assert any(keyword in reply_lower for keyword in scenario["expected_keywords"])
    
    def test_medication_inquiry_flow(self):
        """Test flow for medication-related inquiries."""
        medication_conversation = [
            {
                "user": "What medications help with allergies?",
                "ai": "Common allergy medications include antihistamines like loratadine or cetirizine. However, please consult with a pharmacist or doctor for personalized recommendations."
            },
            {
                "user": "Are there any side effects I should know about?",
                "ai": "Antihistamines can cause drowsiness in some people. It's important to read the medication label and consult with a healthcare professional about potential side effects."
            },
            {
                "user": "Can I take them with other medications?",
                "ai": "Drug interactions are possible. Please consult with your pharmacist or doctor about all medications you're currently taking to ensure safety."
            }
        ]
        
        for exchange in medication_conversation:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = exchange["ai"]
                
                response = self.client.post("/api/chat", json={
                    "message": exchange["user"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert "consult" in data["reply"] or "pharmacist" in data["reply"] or "doctor" in data["reply"]
    
    def test_preventive_care_flow(self):
        """Test flow for preventive care inquiries."""
        preventive_topics = [
            {
                "query": "How often should I get a checkup?",
                "expected_content": ["annual", "yearly", "regular", "doctor"]
            },
            {
                "query": "What vaccines do I need as an adult?",
                "expected_content": ["vaccine", "immunization", "healthcare provider"]
            },
            {
                "query": "How can I maintain good health?",
                "expected_content": ["exercise", "diet", "sleep", "healthy"]
            }
        ]
        
        for topic in preventive_topics:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare advice about {topic['query']}"
                
                response = self.client.post("/api/chat", json={
                    "message": topic["query"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] != REFUSAL_MESSAGE


class TestContentFilteringIntegrationFlows:
    """Test integration flows focusing on content filtering."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        active_tokens.clear()
        
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        self.token = login_response.json()["token"]
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
    
    def test_mixed_query_filtering_flow(self):
        """Test filtering flow with mixed healthcare/non-healthcare queries."""
        mixed_queries = [
            {
                "query": "I have a headache, also what's the weather?",
                "should_process": True,  # Healthcare keyword present
                "reason": "Contains healthcare keyword 'headache'"
            },
            {
                "query": "What's the weather? I also have a fever.",
                "should_process": True,  # Healthcare keyword present
                "reason": "Contains healthcare keyword 'fever'"
            },
            {
                "query": "How to cook pasta and bake bread?",
                "should_process": False,  # No healthcare keywords
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
                    assert data["reply"] != REFUSAL_MESSAGE
            else:
                response = self.client.post("/api/chat", json={
                    "message": test_case["query"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == REFUSAL_MESSAGE
    
    def test_ai_response_filtering_flow(self):
        """Test AI response filtering in the flow."""
        test_scenarios = [
            {
                "user_query": "What are diabetes symptoms?",
                "ai_response": "Sorry, I can only assist with healthcare-related queries.",
                "expected_final": REFUSAL_MESSAGE,
                "reason": "AI incorrectly refused healthcare query"
            },
            {
                "user_query": "What are diabetes symptoms?",
                "ai_response": "Diabetes symptoms include increased thirst, frequent urination, and fatigue.",
                "expected_final": "Diabetes symptoms include increased thirst, frequent urination, and fatigue.",
                "reason": "Valid healthcare response should pass through"
            },
            {
                "user_query": "What are diabetes symptoms?",
                "ai_response": "I don't have information about cooking recipes.",
                "expected_final": REFUSAL_MESSAGE,
                "reason": "AI response indicates non-healthcare topic"
            }
        ]
        
        for scenario in test_scenarios:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = scenario["ai_response"]
                
                response = self.client.post("/api/chat", json={
                    "message": scenario["user_query"],
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == scenario["expected_final"], f"Failed for: {scenario['reason']}"
    
    def test_progressive_filtering_flow(self):
        """Test the progressive filtering system (keyword -> AI -> validation)."""
        # Step 1: Query passes keyword filter
        healthcare_query = "I have been experiencing chest pain"
        
        # Step 2: AI processes and responds
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Chest pain can be serious. Please seek immediate medical attention."
            
            response = self.client.post("/api/chat", json={
                "message": healthcare_query,
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Step 3: Response passes validation and is returned
            assert data["reply"] == "Chest pain can be serious. Please seek immediate medical attention."
            assert data["reply"] != REFUSAL_MESSAGE
        
        # Test case where AI tries to bypass filtering
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            # AI tries to respond to non-healthcare despite system prompt
            mock_openai.return_value = "I can help you with weather information."
            
            response = self.client.post("/api/chat", json={
                "message": healthcare_query,  # Healthcare query
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Should be caught by response validation
            assert data["reply"] == REFUSAL_MESSAGE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])