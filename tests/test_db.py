"""
Unit tests for database functionality.

Tests the ChatLog model, database initialization, session management,
and CRUD operations for the healthcare chatbot database layer.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, ChatLog, init_database, create_chat_log, get_chat_logs_by_query_hash, get_recent_chat_logs


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    # Create test engine and session
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Provide session
    session = TestSessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    os.unlink(db_path)


def test_chat_log_model_creation(test_db):
    """Test ChatLog model creation and basic attributes."""
    # Create a chat log entry
    hashed_query = "a" * 64  # 64-character hash
    hashed_response = "b" * 64
    
    chat_log = ChatLog(
        hashed_query=hashed_query,
        hashed_response=hashed_response
    )
    
    test_db.add(chat_log)
    test_db.commit()
    test_db.refresh(chat_log)
    
    # Verify the entry was created
    assert chat_log.id is not None
    assert chat_log.hashed_query == hashed_query
    assert chat_log.hashed_response == hashed_response
    assert isinstance(chat_log.timestamp, datetime)
    assert chat_log.timestamp <= datetime.utcnow()


def test_create_chat_log_function(test_db):
    """Test the create_chat_log helper function."""
    hashed_query = "test_query_hash"
    hashed_response = "test_response_hash"
    
    # Create chat log using helper function
    chat_log = create_chat_log(test_db, hashed_query, hashed_response)
    
    # Verify the entry
    assert chat_log.id is not None
    assert chat_log.hashed_query == hashed_query
    assert chat_log.hashed_response == hashed_response
    assert isinstance(chat_log.timestamp, datetime)


def test_get_chat_logs_by_query_hash(test_db):
    """Test retrieving chat logs by query hash."""
    # Create multiple chat logs with same query hash
    query_hash = "same_query_hash"
    
    for i in range(3):
        create_chat_log(test_db, query_hash, f"response_hash_{i}")
    
    # Create a different query hash
    create_chat_log(test_db, "different_hash", "different_response")
    
    # Retrieve logs by query hash
    logs = get_chat_logs_by_query_hash(test_db, query_hash)
    
    # Verify results
    assert len(logs) == 3
    for log in logs:
        assert log.hashed_query == query_hash


def test_get_recent_chat_logs(test_db):
    """Test retrieving recent chat logs."""
    # Create multiple chat logs
    for i in range(5):
        create_chat_log(test_db, f"query_{i}", f"response_{i}")
    
    # Retrieve recent logs
    logs = get_recent_chat_logs(test_db, limit=3)
    
    # Verify results (should be ordered by timestamp desc)
    assert len(logs) == 3
    
    # Verify ordering (most recent first)
    for i in range(len(logs) - 1):
        assert logs[i].timestamp >= logs[i + 1].timestamp


def test_chat_log_indexes():
    """Test that the ChatLog model has proper indexes defined."""
    # Check that indexes are defined in table args
    indexes = ChatLog.__table_args__
    
    # Should have 3 indexes
    assert len(indexes) == 3
    
    # Verify index names
    index_names = [idx.name for idx in indexes]
    expected_names = ['idx_hashed_query', 'idx_timestamp', 'idx_query_timestamp']
    
    for name in expected_names:
        assert name in index_names


def test_chat_log_repr(test_db):
    """Test the ChatLog __repr__ method."""
    chat_log = create_chat_log(test_db, "test_query", "test_response")
    
    repr_str = repr(chat_log)
    assert "ChatLog" in repr_str
    assert str(chat_log.id) in repr_str
    assert str(chat_log.timestamp) in repr_str


def test_database_initialization():
    """Test database initialization function."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    try:
        # Set environment variable for test
        original_db_url = os.environ.get("DB_URL")
        os.environ["DB_URL"] = f"sqlite:///{db_path}"
        
        # Test initialization
        init_database()
        
        # Verify database file exists and has tables
        assert os.path.exists(db_path)
        
        # Connect and verify table exists
        test_engine = create_engine(f"sqlite:///{db_path}")
        assert test_engine.has_table("chat_logs")
        
    finally:
        # Cleanup
        if original_db_url:
            os.environ["DB_URL"] = original_db_url
        elif "DB_URL" in os.environ:
            del os.environ["DB_URL"]
        
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_session_management_with_error(test_db):
    """Test that database sessions are properly managed even with errors."""
    # This test verifies that sessions are closed properly
    # even when exceptions occur during database operations
    
    try:
        # Attempt an invalid operation
        test_db.execute("INVALID SQL STATEMENT")
        test_db.commit()
    except Exception:
        # Exception is expected
        pass
    
    # Session should still be usable after rollback
    test_db.rollback()
    
    # Should be able to perform valid operations
    chat_log = create_chat_log(test_db, "test_after_error", "response_after_error")
    assert chat_log.id is not None