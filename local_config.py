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