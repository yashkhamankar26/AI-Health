# Healthcare Chatbot MVP

A secure, AI-powered healthcare chatbot built with FastAPI and Bootstrap. This application provides healthcare assistance through a conversational interface with dual-layer content filtering, authentication, and privacy-preserving logging.

## Features

- 🏥 **Healthcare-Focused AI**: Only responds to healthcare-related queries
- 🔐 **Secure Authentication**: Token-based authentication system
- 🛡️ **Dual-Layer Filtering**: Keyword filtering + AI system prompt filtering
- 📊 **Privacy-Preserving Logging**: Hashed storage of interactions
- 📱 **Responsive Design**: Mobile-first Bootstrap interface
- 🔄 **Fallback System**: Works with or without OpenAI API

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository** (or download the project files)
   ```bash
   git clone <repository-url>
   cd healthcare-chatbot-mvp
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional)
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (see Configuration section)
   ```

4. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application**
   - Open your browser and go to: http://localhost:8000
   - Use demo credentials: `demo@healthcare.com` / `demo123`

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

#### OpenAI API Configuration (Optional)
```bash
# OpenAI API key for AI responses
# If not provided, the system will use mock responses
OPENAI_API_KEY=your_openai_api_key_here
```

#### Database Configuration (Optional)
```bash
# Database connection string
# Defaults to SQLite if not specified
DB_URL=sqlite:///./healthcare_chatbot.db

# For PostgreSQL (example):
# DB_URL=postgresql://username:password@localhost/healthcare_chatbot

# For MySQL (example):
# DB_URL=mysql://username:password@localhost/healthcare_chatbot
```

#### Security Configuration (Optional)
```bash
# Secret key for HMAC hashing
# System will generate one if not provided
APP_SECRET=your_secret_key_for_hmac_hashing
```

#### Demo Credentials (Optional)
```bash
# Demo login credentials for testing
DEMO_EMAIL=demo@healthcare.com
DEMO_PASSWORD=demo123
```

### OpenAI API Key Setup

1. **Get an API key**:
   - Visit https://platform.openai.com/api-keys
   - Create an account or sign in
   - Generate a new API key

2. **Add to environment**:
   ```bash
   # In your .env file
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

3. **Verify setup**:
   - The application will automatically detect the API key
   - Without an API key, the system uses fallback responses

## Usage

### Demo Mode

The application includes demo credentials for immediate testing:

- **Email**: `demo@healthcare.com`
- **Password**: `demo123`

Click "Use Demo Credentials" on the login page to auto-fill these values.

### Healthcare Queries

The chatbot is designed to respond only to healthcare-related questions:

**✅ Supported Topics:**
- Medical conditions and symptoms
- General wellness and nutrition
- Exercise and fitness
- Mental health
- Preventive care
- Medical procedures (general information)
- Medications (general information)

**❌ Blocked Topics:**
- Entertainment, sports, politics
- Technology (unless health-related)
- Financial or legal advice
- Personal advice unrelated to health

### API Endpoints

#### Authentication
```bash
POST /api/login
Content-Type: application/json

{
  "email": "demo@healthcare.com",
  "password": "demo123"
}
```

#### Chat
```bash
POST /api/chat
Content-Type: application/json

{
  "message": "What are the symptoms of a cold?",
  "token": "your_auth_token_here"
}
```

#### Health Check
```bash
GET /health
```

## Development

### Project Structure
```
healthcare-chatbot-mvp/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic data models
│   ├── security.py          # Cryptographic functions
│   ├── content_filter.py    # Healthcare content filtering
│   ├── db.py               # Database configuration
│   └── static/
│       └── index.html      # Frontend interface
├── tests/                  # Test files
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── system_prompt.txt      # AI system prompt
└── README.md             # This file
```

### Running Tests
```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run specific test file
pytest tests/test_authentication.py

# Run with verbose output
pytest -v
```

### Development Server
```bash
# Run with auto-reload for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run on different port
uvicorn app.main:app --reload --port 8080
```

## Deployment

### Production Considerations

1. **Environment Variables**:
   - Set `OPENAI_API_KEY` for full AI functionality
   - Use a production database (PostgreSQL/MySQL)
   - Set a strong `APP_SECRET` for security

2. **Database Setup**:
   ```bash
   # The application automatically creates tables on startup
   # For production, consider running migrations separately
   ```

3. **CORS Configuration**:
   - Update CORS settings in `app/main.py` for production domains
   - Remove wildcard origins (`"*"`) for security

4. **Static Files**:
   - Consider using a CDN for static assets in production
   - Enable gzip compression for better performance

### Docker Deployment (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t healthcare-chatbot .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key healthcare-chatbot
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start
**Problem**: `ModuleNotFoundError` or import errors

**Solutions**:
```bash
# Ensure you're in the project directory
cd healthcare-chatbot-mvp

# Install dependencies
pip install -r requirements.txt

# Check Python version (3.8+ required)
python --version

# Try running with python -m
python -m uvicorn app.main:app --reload
```

#### 2. Database Errors
**Problem**: Database connection or table creation issues

**Solutions**:
```bash
# Check if database file exists and is writable
ls -la healthcare_chatbot.db

# Delete database to recreate (development only)
rm healthcare_chatbot.db

# Check DB_URL format in .env
# SQLite: sqlite:///./healthcare_chatbot.db
# PostgreSQL: postgresql://user:pass@host/db
```

#### 3. OpenAI API Issues
**Problem**: API calls failing or timeout errors

**Solutions**:
```bash
# Verify API key format (starts with sk-)
echo $OPENAI_API_KEY

# Test API key manually
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check network connectivity
ping api.openai.com

# The app works without API key (uses fallback responses)
```

#### 4. Frontend Not Loading
**Problem**: Static files not served or 404 errors

**Solutions**:
```bash
# Check if static files exist
ls -la app/static/

# Verify file permissions
chmod 644 app/static/index.html

# Check FastAPI static mount in main.py
# Should have: app.mount("/static", StaticFiles(directory="app/static"))
```

#### 5. Authentication Issues
**Problem**: Login fails or token validation errors

**Solutions**:
```bash
# Use demo credentials
# Email: demo@healthcare.com
# Password: demo123

# Check if credentials are correct in main.py
# DEMO_CREDENTIALS dictionary

# Clear browser cache/cookies
# Tokens are stored in memory (restart server to clear)
```

#### 6. Content Filtering Too Strict
**Problem**: Healthcare questions being blocked

**Solutions**:
```bash
# Check content_filter.py for keyword list
# Add medical terms if needed

# Verify system_prompt.txt content
cat system_prompt.txt

# Check logs for filtering decisions
# (Enable logging in production for debugging)
```

#### 7. Port Already in Use
**Problem**: `Address already in use` error

**Solutions**:
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Use different port
uvicorn app.main:app --port 8080
```

### Getting Help

1. **Check the logs**: Look for error messages in the terminal
2. **Verify configuration**: Ensure `.env` file is properly formatted
3. **Test components**: Use the `/health` endpoint to check system status
4. **Review requirements**: Ensure all dependencies are installed correctly

### Performance Tips

1. **Database Optimization**:
   - Use PostgreSQL for production
   - Monitor database size (logs grow over time)
   - Consider log rotation for long-running instances

2. **API Optimization**:
   - Monitor OpenAI API usage and costs
   - Implement rate limiting for production
   - Cache common responses if needed

3. **Frontend Optimization**:
   - Enable browser caching for static files
   - Consider minifying CSS/JS for production
   - Use CDN for Bootstrap assets

## Security Notes

- All chat interactions are logged with SHA256/HMAC256 hashing
- No plain text user queries or responses are stored
- Authentication tokens are generated securely
- Content filtering prevents non-healthcare discussions
- CORS should be configured for production domains

## License

This project is provided as-is for educational and development purposes.