"""
Simple tests for chat logging functionality without async.
"""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os
from datetime import datetime

from app.security import hash_for_logging
from app.db import ChatLog


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
    
    def test_no_plain_text_in_hash(self):
        """Test that plain text doesn't appear in hash."""
        sensitive_messages = [
            "I have diabetes and take insulin",
            "My social security number is 123-45-6789",
            "I'm taking medication for depression",
            "My blood pressure is 140/90"
        ]
        
        for message in sensitive_messages:
            hashed = hash_for_logging(message, use_hmac=False)
            
            # Verify no plain text appears in hash
            assert "diabetes" not in hashed.lower()
            assert "insulin" not in hashed.lower()
            assert "123-45-6789" not in hashed
            assert "depression" not in hashed.lower()
            assert "140/90" not in hashed
            
            # Verify hash is different from original
            assert hashed != message
            assert len(hashed) == 64


class TestChatLogModel:
    """Test the ChatLog database model."""
    
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
        if hasattr(self, 'test_engine'):
            self.test_engine.dispose()
        
        if os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except PermissionError:
                pass
    
    def test_chat_log_creation(self):
        """Test creating ChatLog entries."""
        db = self.TestSessionLocal()
        try:
            # Create test hashes
            test_query = "I have a headache"
            test_response = "Try resting and drinking water"
            
            hashed_query = hash_for_logging(test_query, use_hmac=False)
            hashed_response = hash_for_logging(test_response, use_hmac=False)
            
            # Create log entry
            chat_log = ChatLog(
                hashed_query=hashed_query,
                hashed_response=hashed_response
            )
            
            db.add(chat_log)
            db.commit()
            
            # Verify it was saved
            saved_log = db.query(ChatLog).first()
            assert saved_log is not None
            assert saved_log.hashed_query == hashed_query
            assert saved_log.hashed_response == hashed_response
            assert saved_log.timestamp is not None
            assert isinstance(saved_log.timestamp, datetime)
            
            # Verify no plain text in database
            assert test_query not in saved_log.hashed_query
            assert test_response not in saved_log.hashed_response
            
        finally:
            db.close()
    
    def test_multiple_log_entries(self):
        """Test storing multiple log entries."""
        db = self.TestSessionLocal()
        try:
            messages = [
                ("I have a fever", "Monitor your temperature"),
                ("My head hurts", "Try resting in a dark room"),
                ("I feel dizzy", "Sit down and drink water"),
            ]
            
            for query, response in messages:
                chat_log = ChatLog(
                    hashed_query=hash_for_logging(query, use_hmac=False),
                    hashed_response=hash_for_logging(response, use_hmac=False)
                )
                db.add(chat_log)
            
            db.commit()
            
            # Verify all were saved
            logs = db.query(ChatLog).all()
            assert len(logs) == 3
            
            # Verify they have different hashes
            hashes = [log.hashed_query for log in logs]
            assert len(set(hashes)) == 3  # All unique
            
            # Verify no plain text
            for log in logs:
                assert "fever" not in log.hashed_query
                assert "hurts" not in log.hashed_query
                assert "dizzy" not in log.hashed_query
                assert "temperature" not in log.hashed_response
                assert "resting" not in log.hashed_response
                assert "water" not in log.hashed_response
            
        finally:
            db.close()
    
    def test_timestamp_recording(self):
        """Test that timestamps are recorded correctly."""
        db = self.TestSessionLocal()
        try:
            start_time = datetime.utcnow()
            
            chat_log = ChatLog(
                hashed_query=hash_for_logging("test query", use_hmac=False),
                hashed_response=hash_for_logging("test response", use_hmac=False)
            )
            
            db.add(chat_log)
            db.commit()
            
            end_time = datetime.utcnow()
            
            # Verify timestamp is within expected range
            saved_log = db.query(ChatLog).first()
            assert start_time <= saved_log.timestamp <= end_time
            
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])