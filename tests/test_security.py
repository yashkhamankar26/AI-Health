"""
Unit tests for security module.

Tests SHA256 and HMAC256 hashing functions for consistency and proper error handling.
"""

import os
import pytest
from unittest.mock import patch

from app.security import sha256_hex, hmac256_hex, get_secret_key, hash_for_logging


class TestSHA256Functions:
    """Test cases for SHA256 hashing functions."""
    
    def test_sha256_hex_basic(self):
        """Test basic SHA256 hashing functionality."""
        test_data = "Hello, World!"
        expected_hash = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        
        result = sha256_hex(test_data)
        assert result == expected_hash
        assert len(result) == 64  # SHA256 produces 64-character hex string
    
    def test_sha256_hex_empty_string(self):
        """Test SHA256 hashing of empty string."""
        test_data = ""
        expected_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        
        result = sha256_hex(test_data)
        assert result == expected_hash
    
    def test_sha256_hex_consistency(self):
        """Test that SHA256 hashing is consistent across multiple calls."""
        test_data = "healthcare query example"
        
        result1 = sha256_hex(test_data)
        result2 = sha256_hex(test_data)
        result3 = sha256_hex(test_data)
        
        assert result1 == result2 == result3
    
    def test_sha256_hex_different_inputs(self):
        """Test that different inputs produce different hashes."""
        data1 = "healthcare query 1"
        data2 = "healthcare query 2"
        
        hash1 = sha256_hex(data1)
        hash2 = sha256_hex(data2)
        
        assert hash1 != hash2
    
    def test_sha256_hex_type_error(self):
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="Input data must be a string"):
            sha256_hex(123)
        
        with pytest.raises(TypeError, match="Input data must be a string"):
            sha256_hex(None)


class TestHMAC256Functions:
    """Test cases for HMAC256 hashing functions."""
    
    def test_hmac256_hex_with_explicit_key(self):
        """Test HMAC256 hashing with explicitly provided key."""
        test_data = "Hello, World!"
        test_key = "test_secret_key"
        
        result = hmac256_hex(test_data, test_key)
        assert len(result) == 64  # HMAC-SHA256 produces 64-character hex string
        assert isinstance(result, str)
    
    def test_hmac256_hex_consistency_with_same_key(self):
        """Test that HMAC256 is consistent with the same key."""
        test_data = "healthcare query example"
        test_key = "consistent_key"
        
        result1 = hmac256_hex(test_data, test_key)
        result2 = hmac256_hex(test_data, test_key)
        result3 = hmac256_hex(test_data, test_key)
        
        assert result1 == result2 == result3
    
    def test_hmac256_hex_different_keys_different_hashes(self):
        """Test that different keys produce different hashes for same data."""
        test_data = "same data"
        key1 = "key_one"
        key2 = "key_two"
        
        hash1 = hmac256_hex(test_data, key1)
        hash2 = hmac256_hex(test_data, key2)
        
        assert hash1 != hash2
    
    def test_hmac256_hex_different_data_different_hashes(self):
        """Test that different data produces different hashes with same key."""
        key = "same_key"
        data1 = "healthcare query 1"
        data2 = "healthcare query 2"
        
        hash1 = hmac256_hex(data1, key)
        hash2 = hmac256_hex(data2, key)
        
        assert hash1 != hash2
    
    @patch.dict(os.environ, {'APP_SECRET': 'env_test_key'})
    def test_hmac256_hex_with_env_key(self):
        """Test HMAC256 hashing using environment variable key."""
        test_data = "test with env key"
        
        result = hmac256_hex(test_data)
        assert len(result) == 64
        assert isinstance(result, str)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_hmac256_hex_no_env_key_raises_error(self):
        """Test that missing environment key raises ValueError."""
        test_data = "test data"
        
        with pytest.raises(ValueError, match="APP_SECRET environment variable must be set"):
            hmac256_hex(test_data)
    
    def test_hmac256_hex_type_error(self):
        """Test that non-string input raises TypeError."""
        test_key = "test_key"
        
        with pytest.raises(TypeError, match="Input data must be a string"):
            hmac256_hex(123, test_key)
        
        with pytest.raises(TypeError, match="Input data must be a string"):
            hmac256_hex(None, test_key)


class TestSecretKeyManagement:
    """Test cases for environment-based secret key management."""
    
    @patch.dict(os.environ, {'APP_SECRET': 'test_secret_123'})
    def test_get_secret_key_success(self):
        """Test successful retrieval of secret key from environment."""
        result = get_secret_key()
        assert result == 'test_secret_123'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_secret_key_missing_raises_error(self):
        """Test that missing APP_SECRET raises ValueError."""
        with pytest.raises(ValueError, match="APP_SECRET environment variable must be set"):
            get_secret_key()
    
    @patch.dict(os.environ, {'APP_SECRET': ''})
    def test_get_secret_key_empty_raises_error(self):
        """Test that empty APP_SECRET raises ValueError."""
        with pytest.raises(ValueError, match="APP_SECRET environment variable must be set"):
            get_secret_key()


class TestHashForLogging:
    """Test cases for the hash_for_logging utility function."""
    
    @patch.dict(os.environ, {'APP_SECRET': 'logging_test_key'})
    def test_hash_for_logging_with_hmac(self):
        """Test hash_for_logging using HMAC (default behavior)."""
        test_data = "sensitive user query"
        
        result = hash_for_logging(test_data, use_hmac=True)
        assert len(result) == 64
        assert isinstance(result, str)
        
        # Verify it's using HMAC by comparing with direct HMAC call
        expected = hmac256_hex(test_data)
        assert result == expected
    
    def test_hash_for_logging_with_sha256(self):
        """Test hash_for_logging using SHA256."""
        test_data = "user query for sha256"
        
        result = hash_for_logging(test_data, use_hmac=False)
        assert len(result) == 64
        assert isinstance(result, str)
        
        # Verify it's using SHA256 by comparing with direct SHA256 call
        expected = sha256_hex(test_data)
        assert result == expected
    
    @patch.dict(os.environ, {}, clear=True)
    def test_hash_for_logging_fallback_to_sha256(self):
        """Test that hash_for_logging falls back to SHA256 when no secret key."""
        test_data = "fallback test data"
        
        result = hash_for_logging(test_data, use_hmac=True)
        assert len(result) == 64
        assert isinstance(result, str)
        
        # Verify it fell back to SHA256
        expected = sha256_hex(test_data)
        assert result == expected
    
    def test_hash_for_logging_consistency(self):
        """Test that hash_for_logging produces consistent results."""
        test_data = "consistency test"
        
        result1 = hash_for_logging(test_data, use_hmac=False)
        result2 = hash_for_logging(test_data, use_hmac=False)
        
        assert result1 == result2