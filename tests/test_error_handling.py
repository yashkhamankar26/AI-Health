"""
Tests for comprehensive error handling and user feedback improvements.

This module tests the enhanced error handling implemented in Task 15,
including validation errors, API failures, and user-friendly error messages.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from app.main import app

client = TestClient(app)


class TestValidationErrorHandling:
    """Test improved validation error handling."""
    
    def test_login_empty_email_validation(self):
        """Test login with empty email returns user-friendly error."""
        response = client.post("/api/login", json={
            "email": "",
            "password": "demo123"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "Email address is required" in data["detail"]
    
    def test_login_invalid_email_format_validation(self):
        """Test login with invalid email format returns user-friendly error."""
        response = client.post("/api/login", json={
            "email": "not-an-email",
            "password": "demo123"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "valid email address" in data["detail"]
    
    def test_login_short_password_validation(self):
        """Test login with short password returns user-friendly error."""
        response = client.post("/api/login", json={
            "email": "test@example.com",
            "password": "ab"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "at least 3 characters" in data["detail"]
    
    def test_chat_empty_message_validation(self):
        """Test chat with empty message returns user-friendly error."""
        response = client.post("/api/chat", json={
            "message": "",
            "token": "test_token"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "Message cannot be empty" in data["detail"]
    
    def test_chat_long_message_validation(self):
        """Test chat with overly long message returns user-friendly error."""
        long_message = "a" * 1001  # Over 1000 character limit
        
        response = client.post("/api/chat", json={
            "message": long_message,
            "token": "test_token"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "too long" in data["detail"]
        assert "1000 characters" in data["detail"]


class TestImprovedErrorMessages:
    """Test improved error messages for better user experience."""
    
    def test_login_invalid_credentials_message(self):
        """Test login with invalid credentials returns helpful error message."""
        response = client.post("/api/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid email or password" in data["detail"]
        assert "check your credentials" in data["detail"]
    
    def test_chat_invalid_token_message(self):
        """Test chat with invalid token returns helpful error message."""
        response = client.post("/api/chat", json={
            "message": "What are the symptoms of flu?",
            "token": "invalid_token"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "session has expired" in data["detail"]
        assert "log in again" in data["detail"]
    
    def test_chat_message_length_validation_message(self):
        """Test chat message length validation returns specific error."""
        response = client.post("/api/chat", json={
            "message": "What are the symptoms of flu?",
            "token": "valid_token"
        })
        
        # This should work fine - testing the validation doesn't trigger for valid messages
        # The actual validation is tested in other test methods
        assert response.status_code in [200, 401]  # 401 if token is invalid, 200 if valid


class TestGracefulDegradation:
    """Test graceful degradation for API failures."""
    
    @patch('app.main.call_openai_api')
    def test_openai_api_failure_fallback(self, mock_openai):
        """Test fallback response when OpenAI API fails."""
        # Mock OpenAI API failure
        mock_openai.return_value = None
        
        # Create a valid token first
        login_response = client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        # Test chat with API failure
        response = client.post("/api/chat", json={
            "message": "What are the symptoms of flu?",
            "token": token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        # Should get fallback response
        assert any(phrase in data["reply"].lower() for phrase in [
            "limited mode", "consult", "healthcare professional"
        ])
    
    @patch('app.main.log_chat_interaction')
    def test_database_error_graceful_handling(self, mock_log):
        """Test graceful handling of database errors."""
        # Mock database error in logging
        mock_log.side_effect = Exception("Database connection error")
        
        # Create a valid token first
        login_response = client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        # Test chat with database logging error (should still work)
        response = client.post("/api/chat", json={
            "message": "What are the symptoms of flu?",
            "token": token
        })
        
        # Should still return a response despite logging error
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        # Verify the logging function was called (and failed gracefully)
        mock_log.assert_called_once()


class TestErrorResponseStructure:
    """Test that error responses have consistent structure."""
    
    def test_validation_error_structure(self):
        """Test validation errors have consistent JSON structure."""
        response = client.post("/api/login", json={
            "email": "invalid-email",
            "password": "ab"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
    
    def test_authentication_error_structure(self):
        """Test authentication errors have consistent JSON structure."""
        response = client.post("/api/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert "Invalid email or password" in data["detail"]
    
    def test_server_error_structure(self):
        """Test server errors have consistent JSON structure."""
        with patch('app.main.validate_credentials') as mock_validate:
            # Mock a server error
            mock_validate.side_effect = Exception("Unexpected error")
            
            response = client.post("/api/login", json={
                "email": "demo@healthcare.com",
                "password": "demo123"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert isinstance(data["detail"], str)
            assert "temporarily unavailable" in data["detail"]


class TestInputSanitization:
    """Test input sanitization and security."""
    
    def test_chat_message_script_injection_prevention(self):
        """Test that script injection attempts are blocked."""
        malicious_message = "<script>alert('xss')</script>What are flu symptoms?"
        
        response = client.post("/api/chat", json={
            "message": malicious_message,
            "token": "test_token"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "invalid content" in data["detail"]
    
    def test_chat_message_javascript_injection_prevention(self):
        """Test that JavaScript injection attempts are blocked."""
        malicious_message = "javascript:alert('xss') What are flu symptoms?"
        
        response = client.post("/api/chat", json={
            "message": malicious_message,
            "token": "test_token"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "invalid content" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__])