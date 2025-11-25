#!/bin/bash

# RAG API Server Startup Script
# This script starts the Flask API server for the CircuitJS1 RAG integration

echo "=================================="
echo "Starting RAG API Server"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "elektraSage-venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please create it first with: python -m venv elektraSage-venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source elektraSage-venv/bin/activate

# Check if GROQ_API_KEY is set
if [ -z "$GROQ_API_KEY" ]; then
    echo "Warning: GROQ_API_KEY environment variable is not set!"
    echo "Please set it with: export GROQ_API_KEY='your-api-key'"
    echo ""
    read -p "Do you want to enter your API key now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Groq API key: " api_key
        export GROQ_API_KEY="$api_key"
    else
        echo "Continuing without API key (API calls will fail)..."
    fi
fi

# Install/update dependencies
echo ""
echo "Checking dependencies..."
pip install -q flask flask-cors

# Check if embeddings file exists
if [ ! -f "embeddings.joblib" ]; then
    echo ""
    echo "Warning: embeddings.joblib not found!"
    echo "Please generate embeddings first by running: python chunks_embed.py"
    echo ""
fi

# Start the server
echo ""
echo "Starting Flask server on http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo "=================================="
echo ""

python rag_api_server.py
