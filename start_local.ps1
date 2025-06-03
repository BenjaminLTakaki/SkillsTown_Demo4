# projects/skillstown/start_local.ps1

Write-Host "🚀 Starting SkillsTown Local Development Environment" -ForegroundColor Green

# Check if environment variables are set
if (-not $env:OPENAI_API_KEY) {
    Write-Host "⚠️  OPENAI_API_KEY not set" -ForegroundColor Yellow
}

if (-not $env:GROQ_API_KEY) {
    Write-Host "⚠️  GROQ_API_KEY not set" -ForegroundColor Yellow
}

if (-not $env:GEMINI_API_KEY) {
    Write-Host "⚠️  GEMINI_API_KEY not set" -ForegroundColor Yellow
}

# Function to check if a port is in use
function Test-Port {
    param([int]$Port)
    
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
        return $connection
    }
    catch {
        return $false
    }
}

Write-Host ""
Write-Host "📡 Checking required services..." -ForegroundColor Cyan

# Check if Qdrant is running (default port 6333)
if (Test-Port 6333) {
    Write-Host "✅ Qdrant appears to be running" -ForegroundColor Green
} else {
    Write-Host "❌ Qdrant not detected. Start it with: docker run -p 6333:6333 qdrant/qdrant" -ForegroundColor Red
}

# Check if Chisel is running (port 8080)
if (Test-Port 8080) {
    Write-Host "✅ Chisel API is running" -ForegroundColor Green
} else {
    Write-Host "❌ Chisel API not running. Start it in the Chisel directory with: go run ." -ForegroundColor Red
}

# Check if NarreteX is running (port 8100)
if (Test-Port 8100) {
    Write-Host "✅ NarreteX API is running" -ForegroundColor Green
} else {
    Write-Host "❌ NarreteX API not running. Start it in the NarreteX directory with: go run ." -ForegroundColor Red
}

Write-Host ""
Write-Host "🐍 Starting SkillsTown Flask Application..." -ForegroundColor Cyan

# Set Flask environment
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "1"

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

Write-Host "📦 Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt

# Run database migrations
Write-Host "🗄️  Setting up database..." -ForegroundColor Yellow
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"

Write-Host ""
Write-Host "🎉 Starting SkillsTown on http://localhost:5000" -ForegroundColor Green
Write-Host "📚 Access the application at: http://localhost:5000" -ForegroundColor Cyan
Write-Host "🔬 Test podcast generation at: http://localhost:5000/test-podcast" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow

# Start Flask application
python app.py