"""
Unit tests for authentication endpoints in Healthcare Chatbot MVP.

Tests cover login endpoint functionality, credential validation,
token generation, and error handling scenarios.
"""

import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from app.main import app, active_tokens, validate_credentials, generate_demo_token, validate_token


# Create test client
client = TestClient(app)


class TestLoginEndpoint(unittest.TestCase):
    """Test cases for the login endpoint."""
    
    def setUp(self):
        """Clear active tokens before each test."""
        active_tokens.clear()
    
    def test_valid_login_demo_credentials(self):
        """Test successful login with demo credentials."""
        # Test data
        login_data = {
            "email": "demo@healthcare.com",
            "password": "demo123"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["message"] == "Login successful"
        assert len(data["token"]) == 32  # Demo token length
        assert data["token"] in active_tokens
    
    def test_valid_login_user_credentials(self):
        """Test successful login with user credentials."""
        # Test data
        login_data = {
            "email": "user@example.com",
            "password": "password123"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["message"] == "Login successful"
        assert data["token"] in active_tokens
    
    def test_invalid_email(self):
        """Test login with invalid email."""
        # Test data
        login_data = {
            "email": "invalid@example.com",
            "password": "demo123"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid email or password"
    
    def test_invalid_password(self):
        """Test login with invalid password."""
        # Test data
        login_data = {
            "email": "demo@healthcare.com",
            "password": "wrongpassword"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid email or password"
    
    def test_missing_email(self):
        """Test login with missing email field."""
        # Test data
        login_data = {
            "password": "demo123"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 422  # Validation error
    
    def test_missing_password(self):
        """Test login with missing password field."""
        # Test data
        login_data = {
            "email": "demo@healthcare.com"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 422  # Validation error
    
    def test_empty_password(self):
        """Test login with empty password."""
        # Test data
        login_data = {
            "email": "demo@healthcare.com",
            "password": ""
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 422  # Validation error
    
    def test_invalid_email_format(self):
        """Test login with invalid email format."""
        # Test data
        login_data = {
            "email": "not-an-email",
            "password": "demo123"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 422  # Validation error
    
    @patch('app.main.validate_credentials')
    def test_authentication_service_error(self, mock_validate):
        """Test handling of authentication service errors."""
        # Mock an exception in credential validation
        mock_validate.side_effect = Exception("Database connection error")
        
        # Test data
        login_data = {
            "email": "demo@healthcare.com",
            "password": "demo123"
        }
        
        # Make request
        response = client.post("/api/login", json=login_data)
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Authentication service temporarily unavailable" in data["detail"]


class TestCredentialValidation(unittest.TestCase):
    """Test cases for credential validation function."""
    
    def test_validate_demo_credentials(self):
        """Test validation of demo credentials."""
        assert validate_credentials("demo@healthcare.com", "demo123") is True
        assert validate_credentials("user@example.com", "password123") is True
    
    def test_validate_invalid_credentials(self):
        """Test validation of invalid credentials."""
        assert validate_credentials("invalid@example.com", "demo123") is False
        assert validate_credentials("demo@healthcare.com", "wrongpassword") is False
        assert validate_credentials("", "") is False


class TestTokenGeneration(unittest.TestCase):
    """Test cases for token generation and validation."""
    
    def test_generate_demo_token(self):
        """Test demo token generation."""
        email = "test@example.com"
        token = generate_demo_token(email)
        
        # Assertions
        assert isinstance(token, str)
        assert len(token) == 32
        assert token.isalnum()  # Should be alphanumeric
    
    def test_generate_unique_tokens(self):
        """Test that generated tokens are unique."""
        email = "test@example.com"
        token1 = generate_demo_token(email)
        token2 = generate_demo_token(email)
        
        # Tokens should be different even for same email
        assert token1 != token2
    
    def test_validate_token_valid(self):
        """Test validation of valid token."""
        token = "test_token_123"
        active_tokens.add(token)
        
        assert validate_token(token) is True
    
    def test_validate_token_invalid(self):
        """Test validation of invalid token."""
        assert validate_token("invalid_token") is False
    
    def test_validate_token_empty(self):
        """Test validation of empty token."""
        assert validate_token("") is False


class TestLogoutEndpoint(unittest.TestCase):
    """Test cases for the logout endpoint."""
    
    def setUp(self):
        """Clear active tokens before each test."""
        active_tokens.clear()
    
    def test_logout_valid_token(self):
        """Test logout with valid token."""
        # Add token to active tokens
        token = "test_token_123"
        active_tokens.add(token)
        
        # Make request
        response = client.post(f"/api/logout?token={token}")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"
        assert token not in active_tokens
    
    def test_logout_invalid_token(self):
        """Test logout with invalid token."""
        # Make request with non-existent token
        response = client.post("/api/logout?token=invalid_token")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logout successful"


class TestHealthEndpoints(unittest.TestCase):
    """Test cases for health and root endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint response."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "Healthcare Chatbot MVP" in data["message"]
    
    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "healthcare-chatbot-mvp"
        assert data["authentication"] == "enabled"


class TestAuthenticationFlow(unittest.TestCase):
    """Integration tests for complete authentication flow."""
    
    def setUp(self):
        """Clear active tokens before each test."""
        active_tokens.clear()
    
    def test_complete_login_logout_flow(self):
        """Test complete login and logout flow."""
        # Step 1: Login
        login_data = {
            "email": "demo@healthcare.com",
            "password": "demo123"
        }
        
        login_response = client.post("/api/login", json=login_data)
        assert login_response.status_code == 200
        
        login_data = login_response.json()
        token = login_data["token"]
        assert token in active_tokens
        
        # Step 2: Validate token
        assert validate_token(token) is True
        
        # Step 3: Logout
        logout_response = client.post(f"/api/logout?token={token}")
        assert logout_response.status_code == 200
        
        # Step 4: Verify token is invalidated
        assert token not in active_tokens
        assert validate_token(token) is False
    
    def test_multiple_concurrent_logins(self):
        """Test multiple users can login concurrently."""
        # Login with demo credentials
        login_data1 = {
            "email": "demo@healthcare.com",
            "password": "demo123"
        }
        response1 = client.post("/api/login", json=login_data1)
        token1 = response1.json()["token"]
        
        # Login with user credentials
        login_data2 = {
            "email": "user@example.com",
            "password": "password123"
        }
        response2 = client.post("/api/login", json=login_data2)
        token2 = response2.json()["token"]
        
        # Both tokens should be valid
        assert validate_token(token1) is True
        assert validate_token(token2) is True
        assert token1 != token2
        assert len(active_tokens) == 2


if __name__ == "__main__":
    unittest.main()