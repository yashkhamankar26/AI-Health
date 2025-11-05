"""
Data models and validation schemas for the Healthcare Chatbot MVP.

This module contains Pydantic models for API request and response validation,
ensuring proper data structure and type safety across the application.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class LoginIn(BaseModel):
    """
    Model for user login requests.
    
    Validates email format and ensures password is provided.
    Supports Requirement 1.1: User authentication with email and password.
    """
    email: str = Field(
        ..., 
        description="User's email address",
        example="user@example.com"
    )
    password: str = Field(
        ..., 
        min_length=1,
        description="User's password",
        example="password123"
    )
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not v or not v.strip():
            raise ValueError('Email address is required')
        
        email = v.strip().lower()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValueError('Please enter a valid email address')
        
        return email
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password requirements."""
        if not v or not v.strip():
            raise ValueError('Password is required')
        
        if len(v.strip()) < 3:
            raise ValueError('Password must be at least 3 characters long')
        
        return v.strip()


class LoginOut(BaseModel):
    """
    Model for authentication response.
    
    Returns authentication token and success message.
    Supports Requirement 1.1: Return authentication token on successful login.
    """
    token: str = Field(
        ...,
        description="Authentication token for subsequent requests",
        example="demo_token_12345"
    )
    message: str = Field(
        ...,
        description="Success message for the user",
        example="Login successful"
    )


class ChatIn(BaseModel):
    """
    Model for chat message requests.
    
    Validates chat message input and optional authentication token.
    Supports Requirement 2.1: User sends message through chat interface.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's chat message",
        example="What are the symptoms of a common cold?"
    )
    token: Optional[str] = Field(
        None,
        description="Authentication token (optional for demo mode)",
        example="demo_token_12345"
    )
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        """Validate chat message content."""
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        
        message = v.strip()
        
        if len(message) > 1000:
            raise ValueError('Message is too long. Please keep it under 1000 characters.')
        
        if len(message) < 1:
            raise ValueError('Message must contain at least one character')
        
        # Check for potentially harmful content
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                raise ValueError('Message contains invalid content')
        
        return message


class ChatOut(BaseModel):
    """
    Model for AI chat responses.
    
    Wraps AI assistant responses with proper structure.
    Supports Requirement 2.4: System displays AI response with proper formatting.
    """
    reply: str = Field(
        ...,
        description="AI assistant's response to the user query",
        example="Common cold symptoms include runny nose, cough, and mild fever."
    )