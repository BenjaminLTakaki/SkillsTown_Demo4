# projects/skillstown/local_config.py
"""
Local development configuration for SkillsTown
"""
import os

# Local development settings
DEVELOPMENT_MODE = True
DEBUG = True

# API endpoints for local services
NARRETEX_API_URL = "http://localhost:8100"
CHISEL_API_URL = "http://localhost:8080"

# Database URL for local development
LOCAL_DATABASE_URL = "sqlite:///skillstown_local.db"

# File upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# API Keys (set these as environment variables)
REQUIRED_ENV_VARS = [
    'GEMINI_API_KEY',
    'OPENAI_API_KEY', 
    'GROQ_API_KEY'
]

def check_environment():
    """Check if all required environment variables are set"""
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        print(f"Warning: Missing environment variables: {', '.join(missing)}")
        print("Some features may not work correctly.")
    
    return len(missing) == 0

QUIZ_API_BASE_URL = "http://localhost:8081"
QUIZ_API_ACCESS_TOKEN = "kJ9mP2vL8xQ5nR3tY7wZ6cB4dF2gH8jK9lM3nP5qR7sT2uV6wX8yZ9aB3cD5eF7gH2iJ4kL6mN8oP9qR2sT4uV6wX8yZ1aB3cD5eF7gH9iJ2kL"
QUIZ_API_TIMEOUT = 30  # seconds

# Quiz settings
DEFAULT_QUIZ_QUESTIONS = 10
MAX_QUIZ_ATTEMPTS = 5

def get_quiz_api_url():
    """Get the quiz API base URL from environment or config"""
    import os
    return os.environ.get('QUIZ_API_BASE_URL', QUIZ_API_BASE_URL)

# Test function to verify quiz API connectivity
def test_quiz_api_connection():
    """Test if the quiz API is accessible"""
    import requests
    try:
        # Simple health check - adjust endpoint as needed
        response = requests.get(f"{get_quiz_api_url()}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_quiz_headers():
    """Get authenticated headers for quiz API requests"""
    import os
    access_token = os.environ.get('QUIZ_API_ACCESS_TOKEN', QUIZ_API_ACCESS_TOKEN)
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
        