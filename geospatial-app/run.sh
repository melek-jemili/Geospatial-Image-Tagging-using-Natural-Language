#!/bin/bash

# ========================================
# Geospatial Image Analysis - Linux/Mac Launcher
# ========================================

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║     🌍  Geospatial Image Analysis with Quantum Computing    ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ from https://www.python.org"
    exit 1
fi

python3 --version
echo "✅ Python found"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
OPENAI_API_KEY=your_api_key_here
IBM_QUANTUM_CHANNEL=ibm_quantum
FLASK_ENV=development
EOF
    echo "⚠️  Created .env file - Please update with your API keys"
fi

# Create necessary directories
mkdir -p uploads
mkdir -p output
mkdir -p chroma_db

echo ""
echo "🚀 Starting Flask Server..."
echo "📍 Access the application at: http://localhost:5000"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python3 app.py
