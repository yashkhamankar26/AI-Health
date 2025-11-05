"""
Database configuration and models for the Healthcare Chatbot MVP.

This module provides SQLAlchemy configuration, the ChatLog model for storing
hashed chat interactions, and database initialization functionality.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Database configuration
DB_URL = os.getenv("DB_URL", "sqlite:///./healthcare_chatbot.db")

# Create SQLAlchemy engine
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {},
    echo=False  # Set to True for SQL query logging in development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


class ChatLog(Base):
    """
    Model for storing hashed chat interactions.
    
    This model stores hashed versions of user queries and AI responses
    to maintain privacy while enabling system monitoring and analytics.
    """
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hashed_query = Column(String(128), nullable=False, index=True)
    hashed_response = Column(String(128), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Define indexes for optimized query performance
    __table_args__ = (
        Index('idx_hashed_query', 'hashed_query'),
        Index('idx_timestamp', 'timestamp'),
        Index('idx_query_timestamp', 'hashed_query', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<ChatLog(id={self.id}, timestamp={self.timestamp})>"


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    This function provides proper session management with automatic
    cleanup and error handling for FastAPI dependency injection.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    """
    Initialize the database schema.
    
    Creates all tables defined in the Base metadata if they don't exist.
    This function should be called during application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


def create_chat_log(db: Session, hashed_query: str, hashed_response: str) -> ChatLog:
    """
    Create a new chat log entry.
    
    Args:
        db: Database session
        hashed_query: SHA256/HMAC256 hash of user query
        hashed_response: SHA256/HMAC256 hash of AI response
        
    Returns:
        ChatLog: The created chat log entry
    """
    chat_log = ChatLog(
        hashed_query=hashed_query,
        hashed_response=hashed_response,
        timestamp=datetime.utcnow()
    )
    
    db.add(chat_log)
    db.commit()
    db.refresh(chat_log)
    
    return chat_log


def get_chat_logs_by_query_hash(db: Session, hashed_query: str, limit: int = 10) -> list[ChatLog]:
    """
    Retrieve chat logs by hashed query for analytics.
    
    Args:
        db: Database session
        hashed_query: Hash of the query to search for
        limit: Maximum number of results to return
        
    Returns:
        list[ChatLog]: List of matching chat log entries
    """
    return db.query(ChatLog).filter(
        ChatLog.hashed_query == hashed_query
    ).order_by(ChatLog.timestamp.desc()).limit(limit).all()


def get_recent_chat_logs(db: Session, limit: int = 100) -> list[ChatLog]:
    """
    Retrieve recent chat logs for monitoring.
    
    Args:
        db: Database session
        limit: Maximum number of results to return
        
    Returns:
        list[ChatLog]: List of recent chat log entries
    """
    return db.query(ChatLog).order_by(
        ChatLog.timestamp.desc()
    ).limit(limit).all()