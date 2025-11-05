"""
Integration tests for chat logging functionality.
Tests the complete flow from chat endpoint to database logging.
"""

import pytest
from unittest.mock import patch, AsyncMock
import tempfile
import os
from fastapi.testclient import TestClient

from app.main import app
from app.db import ChatLog
from app.security import hash_for_logging


class TestChatLoggingIntegration:
    """Integration tests for chat endpoint with logging."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        self.valid_token = "test_token_integration"
        
        # Add token to active tokens for testing
        from app.main import active_tokens
        active_tokens.add(self.valid_token)
        
        # Create test database
        self.test_db_path = tempfile.mktemp(suffix='.db')
        self.test_db_url = f"sqlite:///{self.test_db_path}"
        
        # Create test engine and session
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db import Base
        
        self.test_engine = create_engine(
            self.test_db_url,
            connect_args={"check_same_thread": False}
        )
        self.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.test_engine)
        
        # Patch the SessionLocal for testing
        self.session_patcher = patch('app.main.SessionLocal', self.TestSessionLocal)
        self.session_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        from app.main import active_tokens
        active_tokens.clear()
        
        # Stop session patching
        self.session_patcher.stop()
        
        # Close the engine to release database connections
        if hasattr(self, 'test_engine'):
            self.test_engine.dispose()
        
        # Clean up test database file
        if os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except PermissionError:
                pass
    
    def test_healthcare_query_logging(self):
        """Test that healthcare queries are logged properly."""
        healthcare_query = "I have been experiencing chest pain"
        expected_ai_response = "Chest pain requires immediate medical attention"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = expected_ai_response
            
            response = self.client.post(
                "/api/chat",
                json={"message": healthcare_query, "token": self.valid_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "medical attention" in data["reply"]
            
            # Verify logging occurred
            db = self.TestSessionLocal()
            try:
                logs = db.query(ChatLog).all()
                assert len(logs) == 1
                
                log_entry = logs[0]
                
                # Verify hashes are correct length
                assert len(log_entry.hashed_query) == 64
                assert len(log_entry.hashed_response) == 64
                
                # Verify no plain text in database
                assert healthcare_query not in log_entry.hashed_query
                assert expected_ai_response not in log_entry.hashed_response
                assert "chest pain" not in log_entry.hashed_query
                assert "medical attention" not in log_entry.hashed_response
                
                # Verify hashes match expected values
                expected_query_hash = hash_for_logging(healthcare_query, use_hmac=True)
                expected_response_hash = hash_for_logging(expected_ai_response, use_hmac=True)
                
                assert log_entry.hashed_query == expected_query_hash
                assert log_entry.hashed_response == expected_response_hash
                
                # Verify timestamp exists
                assert log_entry.timestamp is not None
                
            finally:
                db.close()
    
    def test_non_healthcare_query_logging(self):
        """Test that non-healthcare queries and refusals are logged."""
        non_healthcare_query = "What's the weather today?"
        expected_refusal = "Sorry, I can only assist with healthcare-related queries."
        
        response = self.client.post(
            "/api/chat",
            json={"message": non_healthcare_query, "token": self.valid_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == expected_refusal
        
        # Verify logging occurred
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).all()
            assert len(logs) == 1
            
            log_entry = logs[0]
            
            # Verify no plain text in database
            assert non_healthcare_query not in log_entry.hashed_query
            assert expected_refusal not in log_entry.hashed_response
            assert "weather" not in log_entry.hashed_query
            assert "healthcare-related" not in log_entry.hashed_response
            
            # Verify hashes match expected values
            expected_query_hash = hash_for_logging(non_healthcare_query, use_hmac=True)
            expected_response_hash = hash_for_logging(expected_refusal, use_hmac=True)
            
            assert log_entry.hashed_query == expected_query_hash
            assert log_entry.hashed_response == expected_response_hash
            
        finally:
            db.close()
    
    def test_multiple_interactions_logging(self):
        """Test logging multiple chat interactions."""
        interactions = [
            ("I have a headache", "Try resting and drinking water"),
            ("What's the weather?", "Sorry, I can only assist with healthcare-related queries."),
            ("My blood pressure is high", "Please consult with your doctor")
        ]
        
        for i, (query, expected_response) in enumerate(interactions):
            if "weather" in query:
                # Non-healthcare query - no OpenAI call
                response = self.client.post(
                    "/api/chat",
                    json={"message": query, "token": self.valid_token}
                )
            else:
                # Healthcare query - mock OpenAI response
                with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                    mock_openai.return_value = expected_response
                    
                    response = self.client.post(
                        "/api/chat",
                        json={"message": query, "token": self.valid_token}
                    )
            
            assert response.status_code == 200
        
        # Verify all interactions were logged
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).order_by(ChatLog.id).all()
            assert len(logs) == 3
            
            for i, (query, expected_response) in enumerate(interactions):
                log_entry = logs[i]
                
                # Verify no plain text
                assert query not in log_entry.hashed_query
                assert expected_response not in log_entry.hashed_response
                
                # Verify hashes are correct
                expected_query_hash = hash_for_logging(query, use_hmac=True)
                expected_response_hash = hash_for_logging(expected_response, use_hmac=True)
                
                assert log_entry.hashed_query == expected_query_hash
                assert log_entry.hashed_response == expected_response_hash
            
        finally:
            db.close()
    
    def test_logging_with_api_fallback(self):
        """Test logging when OpenAI API is unavailable."""
        healthcare_query = "I have a fever"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = None  # Simulate API failure
            
            response = self.client.post(
                "/api/chat",
                json={"message": healthcare_query, "token": self.valid_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "limited mode" in data["reply"] or "consult" in data["reply"]
            
            # Verify logging occurred with fallback response
            db = self.TestSessionLocal()
            try:
                logs = db.query(ChatLog).all()
                assert len(logs) == 1
                
                log_entry = logs[0]
                
                # Verify no plain text
                assert healthcare_query not in log_entry.hashed_query
                assert "fever" not in log_entry.hashed_query
                
                # Verify query hash is correct
                expected_query_hash = hash_for_logging(healthcare_query, use_hmac=True)
                assert log_entry.hashed_query == expected_query_hash
                
                # Verify response was logged (even if it's a fallback)
                assert len(log_entry.hashed_response) == 64
                
            finally:
                db.close()
    
    def test_logging_error_handling(self):
        """Test that logging errors don't break the chat flow."""
        healthcare_query = "I have a headache"
        expected_response = "Try resting"
        
        # Mock SessionLocal to raise an exception during logging
        with patch('app.main.SessionLocal') as mock_session_local:
            mock_session = mock_session_local.return_value
            mock_session.add.side_effect = Exception("Database error")
            
            with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
                mock_openai.return_value = expected_response
                
                # This should not raise an exception despite logging failure
                response = self.client.post(
                    "/api/chat",
                    json={"message": healthcare_query, "token": self.valid_token}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["reply"] == expected_response
                
                # Verify logging was attempted
                mock_session_local.assert_called_once()
                mock_session.close.assert_called_once()
    
    def test_logging_without_token(self):
        """Test that logging works even without authentication token."""
        healthcare_query = "I have a headache"
        expected_response = "Try resting and drinking water"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = expected_response
            
            # Send request without token
            response = self.client.post(
                "/api/chat",
                json={"message": healthcare_query}
            )
            
            assert response.status_code == 200
            
            # Verify logging still occurred
            db = self.TestSessionLocal()
            try:
                logs = db.query(ChatLog).all()
                assert len(logs) == 1
                
                log_entry = logs[0]
                
                # Verify hashes are correct
                expected_query_hash = hash_for_logging(healthcare_query, use_hmac=True)
                expected_response_hash = hash_for_logging(expected_response, use_hmac=True)
                
                assert log_entry.hashed_query == expected_query_hash
                assert log_entry.hashed_response == expected_response_hash
                
            finally:
                db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])