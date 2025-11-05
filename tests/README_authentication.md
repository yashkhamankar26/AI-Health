# Authentication Tests

This directory contains comprehensive unit tests for the authentication endpoints in the Healthcare Chatbot MVP.

## Test Coverage

The `test_authentication.py` file covers:

### Login Endpoint Tests
- Valid login with demo credentials
- Valid login with user credentials  
- Invalid email handling
- Invalid password handling
- Missing field validation
- Invalid email format validation
- Authentication service error handling

### Credential Validation Tests
- Demo credentials validation
- Invalid credentials rejection
- Empty credentials handling

### Token Generation and Validation Tests
- Demo token generation
- Token uniqueness verification
- Valid token validation
- Invalid token rejection
- Empty token handling

### Logout Endpoint Tests
- Valid token logout
- Invalid token logout handling

### Health Endpoint Tests
- Root endpoint response
- Health check endpoint response

### Integration Tests
- Complete login/logout flow
- Multiple concurrent user sessions

## Running Tests

### Prerequisites
Install required dependencies:
```bash
pip install fastapi httpx pytest
```

### Running with unittest (recommended)
```bash
python -m unittest tests.test_authentication -v
```

### Running with pytest (if available)
```bash
pytest tests/test_authentication.py -v
```

## Test Results Summary

All tests verify the following requirements:
- **Requirement 1.1**: Return authentication token on valid credentials
- **Requirement 1.2**: Reject login with appropriate error for invalid credentials  
- **Requirement 1.4**: Transition from login view to chat interface on successful authentication

## Authentication Features Tested

1. **Demo Credentials System**: Tests the MVP authentication with predefined demo accounts
2. **Token Generation**: Verifies secure token creation and uniqueness
3. **Token Validation**: Ensures proper token lifecycle management
4. **Error Handling**: Comprehensive error scenarios and appropriate HTTP status codes
5. **Session Management**: Token storage and cleanup functionality

## Security Considerations

The tests verify:
- Proper credential validation
- Secure token generation using hashing
- Token invalidation on logout
- Appropriate error messages without information leakage
- HTTP status code compliance (401 for unauthorized, 422 for validation errors)