#!/bin/bash
# projects/skillstown/start_local.sh

echo "🚀 Starting SkillsTown Local Development Environment"

# Check if environment variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠️  GROQ_API_KEY not set"
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY not set"
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "✅ Port $1 is in use"
        return 0
    else
        echo "❌ Port $1 is not in use"
        return 1
    fi
}

echo ""
echo "📡 Checking required services..."

# Check if Qdrant is running (default port 6333)
if check_port 6333; then
    echo "✅ Qdrant appears to be running"
else
    echo "❌ Qdrant not detected. Start it with: docker run -p 6333:6333 qdrant/qdrant"
fi

# Check if Chisel is running (port 8080)
if check_port 8080; then
    echo "✅ Chisel API is running"
else
    echo "❌ Chisel API not running. Start it in the Chisel directory with: go run ."
fi

# Check if NarreteX is running (port 8100)
if check_port 8100; then
    echo "✅ NarreteX API is running"
else
    echo "❌ NarreteX API not running. Start it in the NarreteX directory with: go run ."
fi

echo ""
echo "🐍 Starting SkillsTown Flask Application..."

# Set Flask environment
export FLASK_ENV=development
export FLASK_DEBUG=1

# Install requirements if not already installed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing requirements..."
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Setting up database..."
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"

echo ""
echo "🎉 Starting SkillsTown on http://localhost:5000"
echo "📚 Access the application at: http://localhost:5000"
echo "🔬 Test podcast generation at: http://localhost:5000/test-podcast"
echo ""
echo "Press Ctrl+C to stop the server"

# Start Flask application
python app.py