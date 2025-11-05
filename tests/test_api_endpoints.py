"""
Comprehensive API endpoint tests with mock data.

Tests all API endpoints with various scenarios including success cases,
error cases, edge cases, and integration scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import json
import tempfile
import os

from app.main import app, active_tokens
from app.content_filter import REFUSAL_MESSAGE


class TestAPIEndpoints:
    """Comprehensive API endpoint tests."""
    
    def setup_method(self):
        """Set up test client and clear tokens."""
        self.client = TestClient(app)
        active_tokens.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()


class TestLoginEndpoint(TestAPIEndpoints):
    """Test cases for /api/login endpoint."""
    
    def test_login_success_demo_credentials(self):
        """Test successful login with demo credentials."""
        response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["message"] == "Login successful"
        assert len(data["token"]) == 32
        assert data["token"] in active_tokens
    
    def test_login_success_user_credentials(self):
        """Test successful login with user credentials."""
        response = self.client.post("/api/login", json={
            "email": "user@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["message"] == "Login successful"
        assert data["token"] in active_tokens
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        test_cases = [
            {"email": "invalid@example.com", "password": "demo123"},
            {"email": "demo@healthcare.com", "password": "wrongpassword"},
            {"email": "nonexistent@test.com", "password": "anypassword"}
        ]
        
        for credentials in test_cases:
            response = self.client.post("/api/login", json=credentials)
            assert response.status_code == 401
            data = response.json()
            assert "Invalid email or password" in data["detail"]
            assert "check your credentials" in data["detail"]
    
    def test_login_validation_errors(self):
        """Test login with validation errors."""
        test_cases = [
            # Missing email
            {"password": "demo123"},
            # Missing password
            {"email": "demo@healthcare.com"},
            # Empty email
            {"email": "", "password": "demo123"},
            # Empty password
            {"email": "demo@healthcare.com", "password": ""},
            # Invalid email format
            {"email": "not-an-email", "password": "demo123"},
            # Short password
            {"email": "demo@healthcare.com", "password": "ab"}
        ]
        
        for credentials in test_cases:
            response = self.client.post("/api/login", json=credentials)
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert isinstance(data["detail"], str)
    
    def test_login_malformed_request(self):
        """Test login with malformed request data."""
        # Invalid JSON
        response = self.client.post("/api/login", data="invalid json")
        assert response.status_code == 422
        
        # Wrong content type
        response = self.client.post("/api/login", data={"email": "test@test.com"})
        assert response.status_code == 422
    
    @patch('app.main.validate_credentials')
    def test_login_server_error(self, mock_validate):
        """Test login with server error."""
        mock_validate.side_effect = Exception("Database connection error")
        
        response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert response.status_code == 500
        data = response.json()
        assert "temporarily unavailable" in data["detail"]
    
    def test_login_case_insensitive_email(self):
        """Test login with case variations in email."""
        response = self.client.post("/api/login", json={
            "email": "DEMO@HEALTHCARE.COM",
            "password": "demo123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
    
    def test_login_whitespace_handling(self):
        """Test login with whitespace in credentials."""
        response = self.client.post("/api/login", json={
            "email": "  demo@healthcare.com  ",
            "password": "  demo123  "
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data


class TestChatEndpoint(TestAPIEndpoints):
    """Test cases for /api/chat endpoint."""
    
    def setup_method(self):
        """Set up test client and valid token."""
        super().setup_method()
        self.valid_token = "test_token_12345"
        active_tokens.add(self.valid_token)
    
    def test_chat_healthcare_query_success(self):
        """Test successful chat with healthcare query."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Headaches can be caused by stress, dehydration, or tension."
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache, what could be causing it?",
                "token": self.valid_token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "headaches" in data["reply"].lower()
            assert data["reply"] != REFUSAL_MESSAGE
            mock_openai.assert_called_once()
    
    def test_chat_non_healthcare_query_rejection(self):
        """Test chat with non-healthcare query gets rejected."""
        non_healthcare_queries = [
            "What's the weather today?",
            "How do I cook pasta?",
            "Tell me a joke",
            "What's the capital of France?",
            "How to fix my computer?"
        ]
        
        for query in non_healthcare_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                response = self.client.post("/api/chat", json={
                    "message": query,
                    "token": self.valid_token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == REFUSAL_MESSAGE
                mock_openai.assert_not_called()
    
    def test_chat_without_token(self):
        """Test chat without authentication token."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a fever, what should I do?"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
    
    def test_chat_invalid_token(self):
        """Test chat with invalid token."""
        response = self.client.post("/api/chat", json={
            "message": "I have a headache",
            "token": "invalid_token"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "session has expired" in data["detail"]
        assert "log in again" in data["detail"]
    
    def test_chat_validation_errors(self):
        """Test chat with validation errors."""
        test_cases = [
            # Empty message
            {"message": "", "token": self.valid_token},
            # Whitespace only message
            {"message": "   ", "token": self.valid_token},
            # Too long message
            {"message": "A" * 1001, "token": self.valid_token},
            # Missing message
            {"token": self.valid_token}
        ]
        
        for chat_data in test_cases:
            response = self.client.post("/api/chat", json=chat_data)
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
    
    def test_chat_malicious_content_rejection(self):
        """Test chat with malicious content gets rejected."""
        malicious_messages = [
            "<script>alert('xss')</script>What are flu symptoms?",
            "javascript:alert('xss') Tell me about diabetes",
            "<img onerror='alert(1)' src='x'>Health question"
        ]
        
        for message in malicious_messages:
            response = self.client.post("/api/chat", json={
                "message": message,
                "token": self.valid_token
            })
            
            assert response.status_code == 400
            data = response.json()
            assert "invalid content" in data["detail"]
    
    def test_chat_openai_api_fallback(self):
        """Test chat fallback when OpenAI API is unavailable."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None  # Simulate API failure
            
            response = self.client.post("/api/chat", json={
                "message": "I have a fever, what should I do?",
                "token": self.valid_token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert any(phrase in data["reply"].lower() for phrase in [
                "limited mode", "consult", "healthcare professional"
            ])
    
    def test_chat_ai_response_validation(self):
        """Test AI response validation and filtering."""
        test_cases = [
            # AI tries to refuse healthcare query
            ("What are diabetes symptoms?", "Sorry, I can only assist with healthcare-related queries.", REFUSAL_MESSAGE),
            # AI responds to non-healthcare despite system prompt
            ("What's the weather?", "I don't have information about weather.", REFUSAL_MESSAGE),
            # Valid healthcare response
            ("What are flu symptoms?", "Flu symptoms include fever, cough, and body aches.", "Flu symptoms include fever, cough, and body aches.")
        ]
        
        for query, ai_response, expected_response in test_cases:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = ai_response
                
                response = self.client.post("/api/chat", json={
                    "message": query,
                    "token": self.valid_token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == expected_response
    
    @patch('app.main.log_chat_interaction', new_callable=AsyncMock)
    def test_chat_logging_integration(self, mock_log):
        """Test that chat interactions are logged."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.valid_token
            })
            
            assert response.status_code == 200
            mock_log.assert_called_once_with("I have a headache", "Healthcare advice")
    
    @patch('app.main.log_chat_interaction', new_callable=AsyncMock)
    def test_chat_logging_error_handling(self, mock_log):
        """Test chat continues working even if logging fails."""
        mock_log.side_effect = Exception("Database error")
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.valid_token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] == "Healthcare advice"
    
    def test_chat_mixed_content_queries(self):
        """Test chat with mixed healthcare and non-healthcare content."""
        mixed_queries = [
            "I have a headache, also what's the weather?",
            "After seeing the doctor, I want to watch a movie",
            "My symptoms include fever, and I'm also hungry for pizza"
        ]
        
        for query in mixed_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare response for: {query}"
                
                response = self.client.post("/api/chat", json={
                    "message": query,
                    "token": self.valid_token
                })
                
                assert response.status_code == 200
                data = response.json()
                # Mixed content with healthcare keywords should be processed
                assert data["reply"] != REFUSAL_MESSAGE
                mock_openai.assert_called_once_with(query)


class TestLogoutEndpoint(TestAPIEndpoints):
    """Test cases for /api/logout endpoint."""
    
    def test_logout_valid_token(self):
        """Test logout with valid token."""
        token = "test_token_logout"
        active_tokens.add(token)
        
        response = self.client.post(f"/api/logout?token={token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"
        assert token not in active_tokens
    
    def test_logout_invalid_token(self):
        """Test logout with invalid token."""
        response = self.client.post("/api/logout?token=invalid_token")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"
    
    def test_logout_missing_token(self):
        """Test logout without token parameter."""
        response = self.client.post("/api/logout")
        
        assert response.status_code == 422  # Missing query parameter


class TestHealthEndpoints(TestAPIEndpoints):
    """Test cases for health and utility endpoints."""
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "healthcare-chatbot-mvp"
        assert data["authentication"] == "enabled"
    
    def test_root_endpoint_serves_html(self):
        """Test root endpoint serves HTML file."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        # Should serve HTML content
        assert response.headers["content-type"].startswith("text/html")


class TestAPIErrorHandling(TestAPIEndpoints):
    """Test API error handling scenarios."""
    
    def test_404_not_found(self):
        """Test 404 for non-existent endpoints."""
        response = self.client.get("/api/nonexistent")
        assert response.status_code == 404
    
    def test_405_method_not_allowed(self):
        """Test 405 for wrong HTTP methods."""
        # GET on POST endpoint
        response = self.client.get("/api/login")
        assert response.status_code == 405
        
        # PUT on POST endpoint
        response = self.client.put("/api/chat")
        assert response.status_code == 405
    
    def test_422_validation_error_structure(self):
        """Test 422 validation error response structure."""
        response = self.client.post("/api/login", json={})
        
        assert response.status_code == 400  # Custom validation handler converts to 400
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
    
    def test_500_server_error_handling(self):
        """Test 500 server error handling."""
        with patch('app.main.validate_credentials') as mock_validate:
            mock_validate.side_effect = Exception("Unexpected error")
            
            response = self.client.post("/api/login", json={
                "email": "demo@healthcare.com",
                "password": "demo123"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "temporarily unavailable" in data["detail"]


class TestAPIIntegrationFlows(TestAPIEndpoints):
    """Test complete API integration flows."""
    
    def test_complete_user_journey(self):
        """Test complete user journey from login to chat to logout."""
        # Step 1: Login
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        token = login_data["token"]
        
        # Step 2: Chat with healthcare query
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Headaches can be caused by various factors."
            
            chat_response = self.client.post("/api/chat", json={
                "message": "I have a headache, what could be causing it?",
                "token": token
            })
            
            assert chat_response.status_code == 200
            chat_data = chat_response.json()
            assert "headaches" in chat_data["reply"].lower()
        
        # Step 3: Chat with non-healthcare query
        non_healthcare_response = self.client.post("/api/chat", json={
            "message": "What's the weather today?",
            "token": token
        })
        
        assert non_healthcare_response.status_code == 200
        non_healthcare_data = non_healthcare_response.json()
        assert non_healthcare_data["reply"] == REFUSAL_MESSAGE
        
        # Step 4: Logout
        logout_response = self.client.post(f"/api/logout?token={token}")
        
        assert logout_response.status_code == 200
        logout_data = logout_response.json()
        assert logout_data["message"] == "Logout successful"
        
        # Step 5: Verify token is invalidated
        invalid_chat_response = self.client.post("/api/chat", json={
            "message": "I have a fever",
            "token": token
        })
        
        assert invalid_chat_response.status_code == 401
    
    def test_concurrent_user_sessions(self):
        """Test multiple concurrent user sessions."""
        # Login multiple users
        users = [
            {"email": "demo@healthcare.com", "password": "demo123"},
            {"email": "user@example.com", "password": "password123"}
        ]
        
        tokens = []
        for user in users:
            response = self.client.post("/api/login", json=user)
            assert response.status_code == 200
            tokens.append(response.json()["token"])
        
        # All tokens should be different
        assert len(set(tokens)) == len(tokens)
        
        # All tokens should work for chat
        for token in tokens:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = "Healthcare advice"
                
                response = self.client.post("/api/chat", json={
                    "message": "I have a headache",
                    "token": token
                })
                
                assert response.status_code == 200
    
    def test_api_resilience_with_failures(self):
        """Test API resilience with various failure scenarios."""
        # Login first
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        # Test chat with OpenAI API failure
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None
            
            response = self.client.post("/api/chat", json={
                "message": "I have a fever",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
        
        # Test chat with logging failure
        with patch('app.main.log_chat_interaction', new_callable=AsyncMock) as mock_log:
            mock_log.side_effect = Exception("Database error")
            
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = "Healthcare advice"
                
                response = self.client.post("/api/chat", json={
                    "message": "I have a headache",
                    "token": token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == "Healthcare advice"


class TestAPIPerformance(TestAPIEndpoints):
    """Test API performance and load scenarios."""
    
    def test_multiple_rapid_requests(self):
        """Test handling multiple rapid requests."""
        # Login first
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        # Send multiple rapid chat requests
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            responses = []
            for i in range(10):
                response = self.client.post("/api/chat", json={
                    "message": f"I have symptom {i}",
                    "token": token
                })
                responses.append(response)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert "reply" in data
    
    def test_large_message_handling(self):
        """Test handling of large messages within limits."""
        # Login first
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        # Test with maximum allowed message size
        large_message = "I have symptoms including " + "pain, " * 180  # Close to 1000 chars
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice for your symptoms"
            
            response = self.client.post("/api/chat", json={
                "message": large_message,
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])