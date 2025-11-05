"""
Tests for chat logging functionality with privacy protection.
Verifies that chat interactions are logged with hashed data and proper timestamps.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
import tempfile
import os
import sqlite3

from app.main import app, log_chat_interaction
from app.db import ChatLog, SessionLocal, init_database, Base, engine
from app.security import hash_for_logging
from app.models import ChatIn


class TestChatLogging:
    """Test cases for chat logging functionality."""
    
    def setup_method(self):
        """Set up test environment with temporary database."""
        self.client = TestClient(app)
        self.valid_token = "test_token_logging"
        
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
                # On Windows, sometimes the file is still locked
                pass
    
    @pytest.mark.asyncio
    async def test_log_chat_interaction_basic(self):
        """Test basic chat interaction logging."""
        user_message = "I have a headache, what should I do?"
        ai_response = "For headaches, you should rest and stay hydrated."
        
        # Call the logging function
        await log_chat_interaction(user_message, ai_response)
        
        # Verify data was stored in database
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).all()
            assert len(logs) == 1
            
            log_entry = logs[0]
            assert log_entry.hashed_query is not None
            assert log_entry.hashed_response is not None
            assert log_entry.timestamp is not None
            assert isinstance(log_entry.timestamp, datetime)
            
            # Verify hashes are correct length (SHA256 = 64 chars, HMAC-SHA256 = 64 chars)
            assert len(log_entry.hashed_query) == 64
            assert len(log_entry.hashed_response) == 64
            
            # Verify hashes are hexadecimal
            assert all(c in '0123456789abcdef' for c in log_entry.hashed_query)
            assert all(c in '0123456789abcdef' for c in log_entry.hashed_response)
            
        finally:
            db.close()
    
    @pytest.mark.asyncio
    async def test_no_plain_text_storage(self):
        """Test that no plain text is stored in the database."""
        user_message = "I have diabetes symptoms like frequent urination"
        ai_response = "Diabetes symptoms include increased thirst and frequent urination. Please consult your doctor."
        
        await log_chat_interaction(user_message, ai_response)
        
        # Check database content directly
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).all()
            assert len(logs) == 1
            
            log_entry = logs[0]
            
            # Verify no plain text appears in hashed fields
            assert user_message not in log_entry.hashed_query
            assert ai_response not in log_entry.hashed_response
            assert "diabetes" not in log_entry.hashed_query.lower()
            assert "urination" not in log_entry.hashed_response.lower()
            
            # Verify hashes are different from original text
            assert log_entry.hashed_query != user_message
            assert log_entry.hashed_response != ai_response
            
        finally:
            db.close()
    
    @pytest.mark.asyncio
    async def test_hash_consistency(self):
        """Test that the same message produces the same hash."""
        user_message = "What are the symptoms of high blood pressure?"
        ai_response = "High blood pressure symptoms may include headaches and dizziness."
        
        # Log the same interaction twice
        await log_chat_interaction(user_message, ai_response)
        await log_chat_interaction(user_message, ai_response)
        
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).all()
            assert len(logs) == 2
            
            # Verify both entries have the same hashes
            assert logs[0].hashed_query == logs[1].hashed_query
            assert logs[0].hashed_response == logs[1].hashed_response
            
            # But different timestamps
            assert logs[0].timestamp != logs[1].timestamp
            
        finally:
            db.close()
    
    @pytest.mark.asyncio
    async def test_different_messages_different_hashes(self):
        """Test that different messages produce different hashes."""
        message1 = "I have a headache"
        response1 = "Try resting and drinking water"
        
        message2 = "I have a fever"
        response2 = "Monitor your temperature and rest"
        
        await log_chat_interaction(message1, response1)
        await log_chat_interaction(message2, response2)
        
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).order_by(ChatLog.id).all()
            assert len(logs) == 2
            
            # Verify hashes are different
            assert logs[0].hashed_query != logs[1].hashed_query
            assert logs[0].hashed_response != logs[1].hashed_response
            
        finally:
            db.close()
    
    @pytest.mark.asyncio
    async def test_logging_with_special_characters(self):
        """Test logging with special characters and unicode."""
        user_message = "I have pain in my chest & it's severe! What should I do? 😰"
        ai_response = "Chest pain can be serious. Please seek immediate medical attention! 🚨"
        
        await log_chat_interaction(user_message, ai_response)
        
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).all()
            assert len(logs) == 1
            
            log_entry = logs[0]
            
            # Verify hashes were created successfully
            assert len(log_entry.hashed_query) == 64
            assert len(log_entry.hashed_response) == 64
            
            # Verify no plain text with special characters
            assert "&" not in log_entry.hashed_query
            assert "😰" not in log_entry.hashed_query
            assert "🚨" not in log_entry.hashed_response
            
        finally:
            db.close()
    
    @pytest.mark.asyncio
    async def test_logging_error_handling(self):
        """Test that logging errors don't break the chat flow."""
        user_message = "I have a headache"
        ai_response = "Try resting"
        
        # Mock database session to raise an exception
        with patch('app.main.SessionLocal') as mock_session_local:
            mock_session = MagicMock()
            mock_session.add.side_effect = Exception("Database error")
            mock_session_local.return_value = mock_session
            
            # This should not raise an exception
            await log_chat_interaction(user_message, ai_response)
            
            # Verify session was attempted to be used
            mock_session_local.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_chat_endpoint_logging_integration(self):
        """Test that the chat endpoint properly logs interactions."""
        healthcare_query = "I have been experiencing chest pain"
        
        with patch('app.main.call_openai_api', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "Chest pain requires immediate medical attention"
            
            with patch('app.main.log_chat_interaction', new_callable=AsyncMock) as mock_log:
                response = self.client.post(
                    "/api/chat",
                    json={"message": healthcare_query, "token": self.valid_token}
                )
                
                assert response.status_code == 200
                
                # Verify logging was called
                mock_log.assert_called_once()
                call_args = mock_log.call_args[0]
                assert call_args[0] == healthcare_query
                assert "medical attention" in call_args[1]
    
    def test_refusal_logging_integration(self):
        """Test that refusal responses are also logged."""
        non_healthcare_query = "What's the weather today?"
        
        with patch('app.main.log_chat_interaction', new_callable=AsyncMock) as mock_log:
            response = self.client.post(
                "/api/chat",
                json={"message": non_healthcare_query, "token": self.valid_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify it's a refusal
            assert "Sorry, I can only assist with healthcare-related queries" in data["reply"]
            
            # Verify logging was called with refusal message
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0]
            assert call_args[0] == non_healthcare_query
            assert "Sorry, I can only assist with healthcare-related queries" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_timestamp_accuracy(self):
        """Test that timestamps are recorded accurately."""
        start_time = datetime.utcnow()
        
        user_message = "I have a fever"
        ai_response = "Monitor your temperature and rest"
        
        await log_chat_interaction(user_message, ai_response)
        
        end_time = datetime.utcnow()
        
        db = self.TestSessionLocal()
        try:
            logs = db.query(ChatLog).all()
            assert len(logs) == 1
            
            log_entry = logs[0]
            
            # Verify timestamp is within expected range
            assert start_time <= log_entry.timestamp <= end_time
            
        finally:
            db.close()
    
    def test_database_schema_verification(self):
        """Test that the database schema is correctly set up for logging."""
        # Check that the table exists and has correct columns
        db = self.TestSessionLocal()
        try:
            # This should not raise an exception
            result = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_logs'")
            tables = result.fetchall()
            assert len(tables) == 1
            
            # Check column structure
            result = db.execute("PRAGMA table_info(chat_logs)")
            columns = result.fetchall()
            
            column_names = [col[1] for col in columns]
            assert 'id' in column_names
            assert 'hashed_query' in column_names
            assert 'hashed_response' in column_names
            assert 'timestamp' in column_names
            
            # Check indexes exist
            result = db.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='chat_logs'")
            indexes = result.fetchall()
            
            index_names = [idx[0] for idx in indexes]
            assert any('hashed_query' in name for name in index_names)
            assert any('timestamp' in name for name in index_names)
            
        finally:
            db.close()


class TestHashingForLogging:
    """Test cases for the hashing functions used in logging."""
    
    def test_hash_for_logging_with_hmac(self):
        """Test hash_for_logging with HMAC enabled."""
        test_message = "I have a headache"
        
        with patch.dict('os.environ', {'APP_SECRET': 'test_secret_key'}):
            hash1 = hash_for_logging(test_message, use_hmac=True)
            hash2 = hash_for_logging(test_message, use_hmac=True)
            
            # Same message should produce same hash
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 hex length
            assert hash1 != test_message
    
    def test_hash_for_logging_fallback_to_sha256(self):
        """Test hash_for_logging falls back to SHA256 when no secret key."""
        test_message = "I have a fever"
        
        # Remove APP_SECRET if it exists
        with patch.dict('os.environ', {}, clear=True):
            hash1 = hash_for_logging(test_message, use_hmac=True)
            hash2 = hash_for_logging(test_message, use_hmac=False)
            
            # Should fall back to SHA256
            assert len(hash1) == 64
            assert hash1 != test_message
            
            # Both should be the same since HMAC falls back to SHA256
            assert hash1 == hash2
    
    def test_hash_for_logging_consistency(self):
        """Test that hashing is consistent across calls."""
        test_messages = [
            "I have diabetes symptoms",
            "What medications help with anxiety?",
            "My blood pressure is high",
            "I'm experiencing chest pain"
        ]
        
        with patch.dict('os.environ', {'APP_SECRET': 'consistent_secret'}):
            for message in test_messages:
                hash1 = hash_for_logging(message, use_hmac=True)
                hash2 = hash_for_logging(message, use_hmac=True)
                
                assert hash1 == hash2
                assert len(hash1) == 64
                assert hash1 != message


class TestDatabaseIntegration:
    """Test database integration for chat logging."""
    
    def setup_method(self):
        """Set up test database."""
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
    
    def teardown_method(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)
    
    def test_database_initialization(self):
        """Test that database is properly initialized."""
        # Check that we can connect and the table exists
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_logs'")
        result = cursor.fetchone()
        assert result is not None
        
        conn.close()
    
    def test_chat_log_model_creation(self):
        """Test creating ChatLog entries directly."""
        db = self.TestSessionLocal()
        try:
            # Create a test log entry
            test_hash_query = "a" * 64  # 64-char hex string
            test_hash_response = "b" * 64  # 64-char hex string
            
            chat_log = ChatLog(
                hashed_query=test_hash_query,
                hashed_response=test_hash_response
            )
            
            db.add(chat_log)
            db.commit()
            
            # Verify it was saved
            saved_log = db.query(ChatLog).first()
            assert saved_log is not None
            assert saved_log.hashed_query == test_hash_query
            assert saved_log.hashed_response == test_hash_response
            assert saved_log.timestamp is not None
            
        finally:
            db.close()
    
    def test_multiple_log_entries(self):
        """Test storing multiple log entries."""
        db = self.TestSessionLocal()
        try:
            # Create multiple entries
            for i in range(5):
                chat_log = ChatLog(
                    hashed_query=f"query_hash_{i:02d}" + "0" * 54,  # Pad to 64 chars
                    hashed_response=f"response_hash_{i:02d}" + "0" * 51  # Pad to 64 chars
                )
                db.add(chat_log)
            
            db.commit()
            
            # Verify all were saved
            logs = db.query(ChatLog).all()
            assert len(logs) == 5
            
            # Verify they have different hashes
            hashes = [log.hashed_query for log in logs]
            assert len(set(hashes)) == 5  # All unique
            
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])