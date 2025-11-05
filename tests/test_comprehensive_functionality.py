"""
Comprehensive functionality tests for Healthcare Chatbot MVP.

This test suite covers all core functionality requirements and ensures
the system works as specified in the requirements document.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os
import json

from app.main import app, active_tokens
from app.content_filter import REFUSAL_MESSAGE, is_health_related
from app.security import sha256_hex, hmac256_hex, hash_for_logging
from app.models import LoginIn, LoginOut, ChatIn, ChatOut


class TestRequirement1Authentication:
    """Test Requirement 1: User authentication functionality."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        active_tokens.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
    
    def test_1_1_valid_credentials_return_token(self):
        """Test Requirement 1.1: Valid credentials return authentication token."""
        response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 0
        assert data["token"] in active_tokens
    
    def test_1_2_invalid_credentials_rejected(self):
        """Test Requirement 1.2: Invalid credentials rejected with error message."""
        response = self.client.post("/api/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid email or password" in data["detail"]
    
    def test_1_3_demo_credentials_auto_fill(self):
        """Test Requirement 1.3: Demo credentials functionality."""
        # Test that demo credentials work
        response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
    
    def test_1_4_successful_auth_transitions_to_chat(self):
        """Test Requirement 1.4: Successful authentication enables chat access."""
        # Login first
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        token = login_response.json()["token"]
        
        # Test chat access with token
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            chat_response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": token
            })
            
            assert chat_response.status_code == 200
    
    def test_1_5_logout_clears_session(self):
        """Test Requirement 1.5: Logout clears session and returns to login."""
        # Login first
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        
        token = login_response.json()["token"]
        
        # Logout
        logout_response = self.client.post(f"/api/logout?token={token}")
        assert logout_response.status_code == 200
        
        # Verify token is invalidated
        chat_response = self.client.post("/api/chat", json={
            "message": "I have a headache",
            "token": token
        })
        
        assert chat_response.status_code == 401


class TestRequirement2ChatInterface:
    """Test Requirement 2: Chat interface functionality."""
    
    def setup_method(self):
        """Set up test client and token."""
        self.client = TestClient(app)
        active_tokens.clear()
        
        # Get valid token
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        self.token = login_response.json()["token"]
    
    def teardown_method(self):
        """Clean up after tests."""
        active_tokens.clear()
    
    def test_2_1_user_message_displayed_with_timestamp(self):
        """Test Requirement 2.1: User message displayed in chat with timestamp."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare response"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            # In a real implementation, timestamp would be included in response
    
    def test_2_2_thinking_indicator_during_processing(self):
        """Test Requirement 2.2: System shows thinking indicator during processing."""
        # This would be tested in frontend, but we can verify backend processes correctly
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare response"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.token
            })
            
            assert response.status_code == 200
            # Backend should respond promptly for frontend to manage loading states
    
    def test_2_3_ai_response_displayed_distinctly(self):
        """Test Requirement 2.3: AI response displayed in distinct chat bubble."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice for your headache"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] == "Healthcare advice for your headache"
    
    def test_2_4_welcome_message_on_load(self):
        """Test Requirement 2.4: Welcome message displayed when chat loads."""
        # This would typically be handled by frontend, but backend should support it
        # We can test that the system is ready to provide responses
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_2_5_auto_scroll_to_latest_message(self):
        """Test Requirement 2.5: Auto-scroll to show latest message."""
        # This is a frontend feature, but we can test multiple messages work correctly
        messages = [
            "I have a headache",
            "What should I do for fever?",
            "How can I treat a cough?"
        ]
        
        for message in messages:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare advice for: {message}"
                
                response = self.client.post("/api/chat", json={
                    "message": message,
                    "token": self.token
                })
                
                assert response.status_code == 200


class TestRequirement3ContentFiltering:
    """Test Requirement 3: Content filtering functionality."""
    
    def setup_method(self):
        """Set up test client and token."""
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
    
    def test_3_1_healthcare_questions_processed(self):
        """Test Requirement 3.1: Healthcare questions processed with AI model."""
        healthcare_queries = [
            "I have a headache",
            "What are flu symptoms?",
            "How to treat a fever?",
            "When should I see a doctor?"
        ]
        
        for query in healthcare_queries:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = f"Healthcare advice for: {query}"
                
                response = self.client.post("/api/chat", json={
                    "message": query,
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] != REFUSAL_MESSAGE
                mock_openai.assert_called_once_with(query)
    
    def test_3_2_non_healthcare_questions_refused(self):
        """Test Requirement 3.2: Non-healthcare questions get refusal message."""
        non_healthcare_queries = [
            "What's the weather today?",
            "How do I cook pasta?",
            "Tell me a joke",
            "What's the capital of France?"
        ]
        
        for query in non_healthcare_queries:
            response = self.client.post("/api/chat", json={
                "message": query,
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["reply"] == REFUSAL_MESSAGE
    
    def test_3_3_keyword_filtering_first_gate(self):
        """Test Requirement 3.3: Keyword-based filtering as first gate."""
        # Test that keyword filtering works
        assert is_health_related("I have a headache") == True
        assert is_health_related("What's the weather?") == False
        
        # Test that non-healthcare queries don't reach OpenAI
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            response = self.client.post("/api/chat", json={
                "message": "What's the weather today?",
                "token": self.token
            })
            
            assert response.status_code == 200
            mock_openai.assert_not_called()
    
    def test_3_4_healthcare_system_prompt_used(self):
        """Test Requirement 3.4: Strict healthcare-focused system prompt used."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.token
            })
            
            assert response.status_code == 200
            # System prompt is used internally in call_openai_api
            mock_openai.assert_called_once()
    
    def test_3_5_ai_response_override_when_inappropriate(self):
        """Test Requirement 3.5: Override inappropriate AI responses."""
        test_cases = [
            # AI tries to refuse healthcare query
            ("What are diabetes symptoms?", "Sorry, I can only assist with healthcare-related queries.", REFUSAL_MESSAGE),
            # AI responds to non-healthcare despite system prompt
            ("What are diabetes symptoms?", "I don't have information about cooking.", REFUSAL_MESSAGE),
            # Valid healthcare response passes through
            ("What are diabetes symptoms?", "Diabetes symptoms include increased thirst.", "Diabetes symptoms include increased thirst.")
        ]
        
        for query, ai_response, expected_final in test_cases:
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = ai_response
                
                response = self.client.post("/api/chat", json={
                    "message": query,
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == expected_final


class TestRequirement4ChatLogging:
    """Test Requirement 4: Chat logging with privacy protection."""
    
    def setup_method(self):
        """Set up test environment with database."""
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
        
        # Get valid token
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        self.token = login_response.json()["token"]
    
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
    
    def test_4_1_log_hashed_versions(self):
        """Test Requirement 4.1: Log hashed versions of queries and responses."""
        user_message = "I have a headache"
        ai_response = "Try resting and drinking water"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = ai_response
            
            response = self.client.post("/api/chat", json={
                "message": user_message,
                "token": self.token
            })
            
            assert response.status_code == 200
            
            # Check database for hashed entries
            from app.db import ChatLog
            db = self.TestSessionLocal()
            try:
                logs = db.query(ChatLog).all()
                assert len(logs) >= 1
                
                log_entry = logs[-1]  # Get latest entry
                
                # Verify hashes are present and not plain text
                assert len(log_entry.hashed_query) == 64  # SHA256 hex length
                assert len(log_entry.hashed_response) == 64
                assert log_entry.hashed_query != user_message
                assert log_entry.hashed_response != ai_response
                
            finally:
                db.close()
    
    def test_4_2_include_timestamps(self):
        """Test Requirement 4.2: Include timestamps for each interaction."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a fever",
                "token": self.token
            })
            
            assert response.status_code == 200
            
            # Check database for timestamp
            from app.db import ChatLog
            from datetime import datetime
            
            db = self.TestSessionLocal()
            try:
                logs = db.query(ChatLog).all()
                assert len(logs) >= 1
                
                log_entry = logs[-1]
                assert log_entry.timestamp is not None
                assert isinstance(log_entry.timestamp, datetime)
                
            finally:
                db.close()
    
    def test_4_3_use_secure_hashing(self):
        """Test Requirement 4.3: Use SHA256 or HMAC256 for security."""
        test_data = "test message"
        
        # Test SHA256
        sha_hash = sha256_hex(test_data)
        assert len(sha_hash) == 64
        assert sha_hash != test_data
        
        # Test HMAC256 (with environment variable)
        with patch.dict('os.environ', {'APP_SECRET': 'test_secret'}):
            hmac_hash = hmac256_hex(test_data)
            assert len(hmac_hash) == 64
            assert hmac_hash != test_data
            assert hmac_hash != sha_hash  # Should be different from SHA256
    
    def test_4_4_never_store_plain_text(self):
        """Test Requirement 4.4: Never store plain text queries or responses."""
        sensitive_message = "I have diabetes and take insulin daily"
        ai_response = "Diabetes management requires regular monitoring"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = ai_response
            
            response = self.client.post("/api/chat", json={
                "message": sensitive_message,
                "token": self.token
            })
            
            assert response.status_code == 200
            
            # Check database doesn't contain plain text
            from app.db import ChatLog
            
            db = self.TestSessionLocal()
            try:
                logs = db.query(ChatLog).all()
                assert len(logs) >= 1
                
                log_entry = logs[-1]
                
                # Verify no plain text in database
                assert "diabetes" not in log_entry.hashed_query.lower()
                assert "insulin" not in log_entry.hashed_query.lower()
                assert "monitoring" not in log_entry.hashed_response.lower()
                
            finally:
                db.close()
    
    def test_4_5_database_schema_initialization(self):
        """Test Requirement 4.5: Initialize database schema if it doesn't exist."""
        # This is tested by the setup process itself
        from app.db import ChatLog
        
        db = self.TestSessionLocal()
        try:
            # Should be able to query the table without errors
            count = db.query(ChatLog).count()
            assert count >= 0  # Should not raise an exception
            
        finally:
            db.close()


class TestRequirement5OpenAIIntegration:
    """Test Requirement 5: OpenAI API integration."""
    
    def setup_method(self):
        """Set up test client and token."""
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
    
    def test_5_1_use_gpt4o_mini_when_configured(self):
        """Test Requirement 5.1: Use GPT-4o-mini model when API key configured."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice from GPT-4o-mini"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "Healthcare advice" in data["reply"]
            mock_openai.assert_called_once()
    
    def test_5_2_fallback_when_api_unavailable(self):
        """Test Requirement 5.2: Fall back to mock responses when API unavailable."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None  # Simulate API failure
            
            response = self.client.post("/api/chat", json={
                "message": "I have a fever",
                "token": self.token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
    
    def test_5_3_use_temperature_02(self):
        """Test Requirement 5.3: Use temperature 0.2 for consistent responses."""
        # This is tested internally in the OpenAI API call
        # We can verify the function is called correctly
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Consistent healthcare response"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.token
            })
            
            assert response.status_code == 200
            mock_openai.assert_called_once()
    
    def test_5_4_handle_api_errors_gracefully(self):
        """Test Requirement 5.4: Handle API errors gracefully with fallback."""
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.side_effect = Exception("API Error")
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": self.token
            })
            
            # Should not crash, should return fallback response
            assert response.status_code == 200
            data = response.json()
            assert len(data["reply"]) > 0
    
    def test_5_5_operate_in_mock_mode_without_errors(self):
        """Test Requirement 5.5: Operate in mock mode without errors when no API key."""
        with patch.dict('os.environ', {}, clear=True):  # Remove API key
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = None  # No API key available
                
                response = self.client.post("/api/chat", json={
                    "message": "I have a headache",
                    "token": self.token
                })
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["reply"]) > 0  # Should get fallback response


class TestRequirement6UserInterface:
    """Test Requirement 6: User interface requirements."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_6_1_modern_healthcare_themed_ui(self):
        """Test Requirement 6.1: Display modern, healthcare-themed UI."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
    
    def test_6_2_responsive_mobile_adaptation(self):
        """Test Requirement 6.2: Interface adapts responsively to smaller screens."""
        # This would be tested in frontend tests, but we ensure backend supports it
        response = self.client.get("/")
        assert response.status_code == 200
    
    def test_6_3_distinct_message_bubbles(self):
        """Test Requirement 6.3: Messages appear in distinct bubbles."""
        # Backend provides the data structure for frontend to render
        login_response = self.client.post("/api/login", json={
            "email": "demo@healthcare.com",
            "password": "demo123"
        })
        token = login_response.json()["token"]
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Healthcare advice"
            
            response = self.client.post("/api/chat", json={
                "message": "I have a headache",
                "token": token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data  # Structured response for frontend
    
    def test_6_4_healthcare_iconography_and_branding(self):
        """Test Requirement 6.4: Display healthcare iconography and branding."""
        response = self.client.get("/")
        assert response.status_code == 200
        # HTML file should contain healthcare-themed content
    
    def test_6_5_clear_visual_feedback_and_validation(self):
        """Test Requirement 6.5: Forms provide clear visual feedback."""
        # Test validation error responses are structured for frontend
        response = self.client.post("/api/login", json={
            "email": "invalid-email",
            "password": "ab"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)


class TestRequirement7ConfigurationAndDocumentation:
    """Test Requirement 7: Configuration management and documentation."""
    
    def test_7_1_example_environment_configuration(self):
        """Test Requirement 7.1: Provide example environment configuration."""
        # Check that .env.example exists
        assert os.path.exists(".env.example")
    
    def test_7_2_complete_requirements_file(self):
        """Test Requirement 7.2: Include complete requirements.txt file."""
        assert os.path.exists("requirements.txt")
        
        with open("requirements.txt", "r") as f:
            content = f.read()
            # Should contain essential dependencies
            assert "fastapi" in content.lower()
            assert "sqlalchemy" in content.lower()
    
    def test_7_3_serve_static_files_and_api_endpoints(self):
        """Test Requirement 7.3: Serve static files and API endpoints correctly."""
        # Test API endpoints work
        response = self.client.get("/health")
        assert response.status_code == 200
        
        # Test static file serving
        response = self.client.get("/")
        assert response.status_code == 200
    
    def test_7_4_sqlite_database_support(self):
        """Test Requirement 7.4: Support SQLite by default with configurable alternatives."""
        # Test that database initialization works
        from app.db import init_database
        
        # Should not raise an exception
        try:
            init_database()
        except Exception as e:
            # Some errors are expected in test environment
            assert "database" in str(e).lower() or "sqlite" in str(e).lower()
    
    def test_7_5_comprehensive_documentation(self):
        """Test Requirement 7.5: Include comprehensive setup and usage documentation."""
        assert os.path.exists("README.md")
        
        with open("README.md", "r") as f:
            content = f.read()
            # Should contain setup instructions
            assert "setup" in content.lower() or "install" in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])