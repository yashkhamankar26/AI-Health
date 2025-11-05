"""
Security module for healthcare chatbot MVP.

Provides cryptographic functions for secure data hashing and environment-based
secret key management to protect user privacy and ensure data integrity.
"""

import hashlib
import hmac
import os
from typing import Optional


def get_secret_key() -> str:
    """
    Get the secret key from environment variables.
    
    Returns:
        str: The secret key for HMAC operations
        
    Raises:
        ValueError: If APP_SECRET environment variable is not set
    """
    secret = os.getenv('APP_SECRET')
    if not secret:
        raise ValueError("APP_SECRET environment variable must be set")
    return secret


def sha256_hex(data: str) -> str:
    """
    Generate SHA256 hash of the input data.
    
    Args:
        data (str): The input string to hash
        
    Returns:
        str: Hexadecimal representation of the SHA256 hash
    """
    if not isinstance(data, str):
        raise TypeError("Input data must be a string")
    
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def hmac256_hex(data: str, secret_key: Optional[str] = None) -> str:
    """
    Generate HMAC-SHA256 hash of the input data using a secret key.
    
    Args:
        data (str): The input string to hash
        secret_key (str, optional): The secret key for HMAC. If None, uses environment variable
        
    Returns:
        str: Hexadecimal representation of the HMAC-SHA256 hash
        
    Raises:
        TypeError: If input data is not a string
        ValueError: If secret key is not available
    """
    if not isinstance(data, str):
        raise TypeError("Input data must be a string")
    
    if secret_key is None:
        secret_key = get_secret_key()
    
    return hmac.new(
        secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def hash_for_logging(data: str, use_hmac: bool = True) -> str:
    """
    Hash data for secure logging purposes.
    
    Args:
        data (str): The data to hash for logging
        use_hmac (bool): Whether to use HMAC (more secure) or plain SHA256
        
    Returns:
        str: Hashed representation of the data
    """
    if use_hmac:
        try:
            return hmac256_hex(data)
        except ValueError:
            # Fallback to SHA256 if no secret key is available
            return sha256_hex(data)
    else:
        return sha256_hex(data)