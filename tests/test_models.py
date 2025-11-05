"""
Unit tests for Pydantic models and validation schemas.

Tests all data models for proper validation, error handling,
and field constraints in the Healthcare Chatbot MVP.
"""

import pytest
from pydantic import ValidationError

from app.models import LoginIn, LoginOut, ChatIn, ChatOut


class TestLoginInModel:
    """Test cases for LoginIn model validation."""
    
    def test_valid_login_data(self):
        """Test LoginIn with valid data."""
        valid_data = {
            "email": "user@example.com",
            "password": "password123"
        }
        
        login = LoginIn(**valid_data)
        assert login.email == "user@example.com"
        assert login.password == "password123"
    
    def test_email_validation_success(self):
        """Test successful email validation."""
        valid_emails = [
            "user@example.com",
            "test.user@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com"
        ]
        
        for email in valid_emails:
            login = LoginIn(email=email, password="password123")
            assert login.email == email.lower()
    
    def test_email_validation_failure(self):
        """Test email validation failures."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user.example.com",
            "",
            "   ",
            "user@.com",
            "user@domain.",
            "user space@example.com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                LoginIn(email=email, password="password123")
            
            errors = exc_info.value.errors()
            assert any("email" in str(error) for error in errors)
    
    def test_password_validation_success(self):
        """Test successful password validation."""
        valid_passwords = [
            "abc",  # Minimum 3 characters
            "password123",
            "complex_password!@#",
            "   password   "  # Should be stripped
        ]
        
        for password in valid_passwords:
            login = LoginIn(email="user@example.com", password=password)
            assert login.password == password.strip()
    
    def test_password_validation_failure(self):
        """Test password validation failures."""
        invalid_passwords = [
            "",
            "   ",
            "ab",  # Too short
            None
        ]
        
        for password in invalid_passwords:
            with pytest.raises(ValidationError) as exc_info:
                if password is None:
                    LoginIn(email="user@example.com")
                else:
                    LoginIn(email="user@example.com", password=password)
            
            errors = exc_info.value.errors()
            assert any("password" in str(error) for error in errors)
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        # Missing email
        with pytest.raises(ValidationError) as exc_info:
            LoginIn(password="password123")
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('email',) for error in errors)
        
        # Missing password
        with pytest.raises(ValidationError) as exc_info:
            LoginIn(email="user@example.com")
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('password',) for error in errors)
    
    def test_email_case_normalization(self):
        """Test that email is normalized to lowercase."""
        login = LoginIn(email="USER@EXAMPLE.COM", password="password123")
        assert login.email == "user@example.com"
    
    def test_password_whitespace_stripping(self):
        """Test that password whitespace is stripped."""
        login = LoginIn(email="user@example.com", password="  password123  ")
        assert login.password == "password123"


class TestLoginOutModel:
    """Test cases for LoginOut model."""
    
    def test_valid_login_response(self):
        """Test LoginOut with valid data."""
        response_data = {
            "token": "demo_token_12345",
            "message": "Login successful"
        }
        
        response = LoginOut(**response_data)
        assert response.token == "demo_token_12345"
        assert response.message == "Login successful"
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        # Missing token
        with pytest.raises(ValidationError) as exc_info:
            LoginOut(message="Login successful")
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('token',) for error in errors)
        
        # Missing message
        with pytest.raises(ValidationError) as exc_info:
            LoginOut(token="demo_token_12345")
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('message',) for error in errors)
    
    def test_empty_string_validation(self):
        """Test validation with empty strings."""
        # Empty token should fail
        with pytest.raises(ValidationError):
            LoginOut(token="", message="Login successful")
        
        # Empty message should fail
        with pytest.raises(ValidationError):
            LoginOut(token="demo_token_12345", message="")


class TestChatInModel:
    """Test cases for ChatIn model validation."""
    
    def test_valid_chat_data(self):
        """Test ChatIn with valid data."""
        valid_data = {
            "message": "What are the symptoms of flu?",
            "token": "demo_token_12345"
        }
        
        chat = ChatIn(**valid_data)
        assert chat.message == "What are the symptoms of flu?"
        assert chat.token == "demo_token_12345"
    
    def test_valid_chat_without_token(self):
        """Test ChatIn without token (optional field)."""
        chat = ChatIn(message="What are the symptoms of flu?")
        assert chat.message == "What are the symptoms of flu?"
        assert chat.token is None
    
    def test_message_validation_success(self):
        """Test successful message validation."""
        valid_messages = [
            "What are flu symptoms?",
            "I have a headache and need help",
            "My blood pressure is high, what should I do?",
            "   Message with whitespace   ",  # Should be stripped
            "A" * 1000  # Maximum length
        ]
        
        for message in valid_messages:
            chat = ChatIn(message=message)
            assert chat.message == message.strip()
    
    def test_message_validation_failure(self):
        """Test message validation failures."""
        invalid_messages = [
            "",
            "   ",
            "A" * 1001,  # Too long
            None
        ]
        
        for message in invalid_messages:
            with pytest.raises(ValidationError) as exc_info:
                if message is None:
                    ChatIn()
                else:
                    ChatIn(message=message)
            
            errors = exc_info.value.errors()
            assert any("message" in str(error) for error in errors)
    
    def test_message_security_validation(self):
        """Test message validation for security threats."""
        malicious_messages = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img onerror='alert(1)' src='x'>",
            "onclick='alert(1)'",
            "onload='malicious()'"
        ]
        
        for message in malicious_messages:
            with pytest.raises(ValidationError) as exc_info:
                ChatIn(message=message)
            
            errors = exc_info.value.errors()
            assert any("invalid content" in str(error) for error in errors)
    
    def test_message_length_constraints(self):
        """Test message length constraints."""
        # Test minimum length (1 character after stripping)
        chat = ChatIn(message="A")
        assert chat.message == "A"
        
        # Test maximum length (1000 characters)
        max_message = "A" * 1000
        chat = ChatIn(message=max_message)
        assert chat.message == max_message
        
        # Test over maximum length
        with pytest.raises(ValidationError):
            ChatIn(message="A" * 1001)
    
    def test_message_whitespace_handling(self):
        """Test message whitespace handling."""
        chat = ChatIn(message="   What are flu symptoms?   ")
        assert chat.message == "What are flu symptoms?"
    
    def test_token_optional_field(self):
        """Test that token field is optional."""
        # With token
        chat_with_token = ChatIn(message="Test message", token="token123")
        assert chat_with_token.token == "token123"
        
        # Without token
        chat_without_token = ChatIn(message="Test message")
        assert chat_without_token.token is None
        
        # With None token
        chat_none_token = ChatIn(message="Test message", token=None)
        assert chat_none_token.token is None


class TestChatOutModel:
    """Test cases for ChatOut model."""
    
    def test_valid_chat_response(self):
        """Test ChatOut with valid data."""
        response_data = {
            "reply": "Common cold symptoms include runny nose, cough, and mild fever."
        }
        
        response = ChatOut(**response_data)
        assert response.reply == "Common cold symptoms include runny nose, cough, and mild fever."
    
    def test_missing_reply_field(self):
        """Test validation with missing reply field."""
        with pytest.raises(ValidationError) as exc_info:
            ChatOut()
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('reply',) for error in errors)
    
    def test_empty_reply_validation(self):
        """Test validation with empty reply."""
        # Empty string should fail
        with pytest.raises(ValidationError):
            ChatOut(reply="")
    
    def test_various_reply_types(self):
        """Test ChatOut with various reply content."""
        valid_replies = [
            "Simple response",
            "Multi-line\nresponse with\nnewlines",
            "Response with special characters: !@#$%^&*()",
            "Response with unicode: 🏥 💊 🩺",
            "Very long response: " + "A" * 500
        ]
        
        for reply in valid_replies:
            response = ChatOut(reply=reply)
            assert response.reply == reply


class TestModelIntegration:
    """Integration tests for model interactions."""
    
    def test_login_flow_models(self):
        """Test complete login flow with models."""
        # Create login request
        login_request = LoginIn(
            email="user@example.com",
            password="password123"
        )
        
        # Simulate successful login response
        login_response = LoginOut(
            token="generated_token_12345",
            message="Login successful"
        )
        
        assert login_request.email == "user@example.com"
        assert login_request.password == "password123"
        assert login_response.token == "generated_token_12345"
        assert login_response.message == "Login successful"
    
    def test_chat_flow_models(self):
        """Test complete chat flow with models."""
        # Create chat request
        chat_request = ChatIn(
            message="What are the symptoms of diabetes?",
            token="valid_token_123"
        )
        
        # Simulate AI response
        chat_response = ChatOut(
            reply="Diabetes symptoms include increased thirst, frequent urination, and fatigue."
        )
        
        assert chat_request.message == "What are the symptoms of diabetes?"
        assert chat_request.token == "valid_token_123"
        assert "diabetes symptoms" in chat_response.reply.lower()
    
    def test_model_serialization(self):
        """Test model serialization to dict."""
        login_in = LoginIn(email="user@example.com", password="password123")
        login_out = LoginOut(token="token123", message="Success")
        chat_in = ChatIn(message="Test message", token="token123")
        chat_out = ChatOut(reply="Test reply")
        
        # Test dict conversion
        assert login_in.model_dump() == {"email": "user@example.com", "password": "password123"}
        assert login_out.model_dump() == {"token": "token123", "message": "Success"}
        assert chat_in.model_dump() == {"message": "Test message", "token": "token123"}
        assert chat_out.model_dump() == {"reply": "Test reply"}
    
    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        chat_out = ChatOut(reply="Test reply with special chars: 🏥")
        
        # Should be able to serialize to JSON
        json_str = chat_out.model_dump_json()
        assert "Test reply with special chars" in json_str
        
        # Should be able to parse back
        parsed = ChatOut.model_validate_json(json_str)
        assert parsed.reply == chat_out.reply


class TestModelErrorMessages:
    """Test model validation error messages."""
    
    def test_login_error_messages(self):
        """Test LoginIn validation error messages."""
        # Test invalid email
        with pytest.raises(ValidationError) as exc_info:
            LoginIn(email="invalid-email", password="password123")
        
        errors = exc_info.value.errors()
        email_error = next(error for error in errors if error['loc'] == ('email',))
        assert "valid email address" in email_error['msg']
        
        # Test short password
        with pytest.raises(ValidationError) as exc_info:
            LoginIn(email="user@example.com", password="ab")
        
        errors = exc_info.value.errors()
        password_error = next(error for error in errors if error['loc'] == ('password',))
        assert "at least 3 characters" in password_error['msg']
    
    def test_chat_error_messages(self):
        """Test ChatIn validation error messages."""
        # Test empty message
        with pytest.raises(ValidationError) as exc_info:
            ChatIn(message="")
        
        errors = exc_info.value.errors()
        message_error = next(error for error in errors if error['loc'] == ('message',))
        assert "cannot be empty" in message_error['msg']
        
        # Test long message
        with pytest.raises(ValidationError) as exc_info:
            ChatIn(message="A" * 1001)
        
        errors = exc_info.value.errors()
        message_error = next(error for error in errors if error['loc'] == ('message',))
        assert "too long" in message_error['msg']
        
        # Test malicious content
        with pytest.raises(ValidationError) as exc_info:
            ChatIn(message="<script>alert('xss')</script>")
        
        errors = exc_info.value.errors()
        message_error = next(error for error in errors if error['loc'] == ('message',))
        assert "invalid content" in message_error['msg']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])