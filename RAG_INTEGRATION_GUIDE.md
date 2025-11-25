# AI Chatbot RAG Integration Guide

## Overview

The AI Chatbot in CircuitJS1 is now integrated with your RAG (Retrieval-Augmented Generation) system. This allows users to ask questions about circuits and automatically generate circuit designs based on natural language queries.

## Architecture

```
┌─────────────────────┐
│  CircuitJS1 (GWT)   │
│  AIChatbotDialog    │
└──────────┬──────────┘
           │ HTTP POST
           │ (JSON)
           ▼
┌─────────────────────┐
│  Flask API Server   │
│  rag_api_server.py  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   RAG System        │
│ - chunks_embed.py   │
│ - Groq API          │
│ - embeddings.joblib │
└─────────────────────┘
```

## Setup Instructions

### 1. Install Python Dependencies

```bash
cd add/
source elektraSage-venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Up Groq API Key

```bash
export GROQ_API_KEY='your-groq-api-key-here'
```

To make it permanent, add to your `~/.bashrc` or `~/.zshrc`:
```bash
echo 'export GROQ_API_KEY="your-groq-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Generate Embeddings (if not already done)

```bash
cd add/
python chunks_embed.py
```

This will create `embeddings.joblib` with vector embeddings of your circuit database.

### 4. Start the RAG API Server

Option A - Using the startup script:
```bash
cd add/
./start_rag_server.sh
```

Option B - Manual start:
```bash
cd add/
source elektraSage-venv/bin/activate
python rag_api_server.py
```

The server will start on `http://localhost:5000`

### 5. Build and Run CircuitJS1

```bash
# In the main project directory
./dev.sh
```

Or use your existing build process.

## API Endpoints

### Health Check
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "ok",
  "embeddings_loaded": true,
  "circuits_available": 150
}
```

### Circuit Generation (RAG Query)
```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Create a simple LED circuit with a resistor"}'
```

Response:
```json
{
  "success": true,
  "response": "Circuit generated successfully!",
  "circuit_text": "$ 1 0.000005 10.20027730826997...",
  "retrieved_circuits": [
    {"name": "LED Circuit", "similarity": 0.892}
  ],
  "keywords": "LED resistor simple circuit"
}
```

### Simple Questions (No Circuit Generation)
```bash
curl -X POST http://localhost:5000/simple-query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is a resistor?"}'
```

Response:
```json
{
  "success": true,
  "response": "A resistor is a passive electronic component..."
}
```

## Using the Chatbot in CircuitJS1

1. **Open CircuitJS1** in your browser
2. **Click "AI Assistant"** in the menubar
3. **Select "Open AI Chatbot"**
4. **Type your question** or circuit request
5. **Press Enter or click Send**

### Example Queries

**Simple Questions:**
- "What is a diode?"
- "Explain Ohm's Law"
- "How does a capacitor work?"

**Circuit Generation:**
- "Create a simple LED circuit"
- "Generate a voltage divider with 10k resistors"
- "Build an RC filter circuit"
- "Design a full-wave rectifier"

### Import Generated Circuits

1. Ask for a circuit (e.g., "Create an LED circuit")
2. Wait for the AI to generate the circuit
3. Click the **"Import Circuit"** button
4. The circuit will load into the simulator

## Configuration

### Change API Server URL

Edit `/src/com/lushprojects/circuitjs1/client/AIChatbotDialog.java`:

```java
private static final String RAG_API_URL = "http://localhost:5000";
```

Change to your server's URL if running remotely.

### Adjust RAG Parameters

Edit `/add/rag_api_server.py`:

```python
# Number of similar circuits to retrieve
top_result = 5  # Change this value

# Groq model settings
model="llama-3.3-70b-versatile",
temperature=0.1,  # Lower = more deterministic
max_tokens=8000,  # Maximum response length
```

## Troubleshooting

### "Connection error" in chatbot

**Problem:** Flask server not running
**Solution:**
```bash
cd add/
./start_rag_server.sh
```

### "GROQ_API_KEY not set"

**Problem:** Missing API key
**Solution:**
```bash
export GROQ_API_KEY='your-key-here'
```

### "Embeddings not loaded"

**Problem:** Missing embeddings.joblib
**Solution:**
```bash
cd add/
python chunks_embed.py
```

### CORS errors in browser

**Problem:** Cross-origin request blocked
**Solution:** Flask-CORS is already configured, but if running on different domains:
```python
# In rag_api_server.py
CORS(app, origins=["http://your-domain.com"])
```

### Slow responses

**Problem:** Large circuit database or complex queries
**Solution:**
- Reduce `top_result` value
- Use faster Groq model
- Pre-filter circuits by category

## Development Tips

### Testing the API

Use curl or Postman to test endpoints:
```bash
# Test health
curl http://localhost:5000/health

# Test query
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test circuit"}'
```

### Viewing Logs

Flask server logs appear in the terminal where you started `rag_api_server.py`

### Debug Mode

The Flask server runs in debug mode by default. For production:
```python
# In rag_api_server.py
app.run(host='0.0.0.0', port=5000, debug=False)
```

## File Structure

```
elektraSage-rag/
├── add/
│   ├── rag_api_server.py          # Flask API server (NEW)
│   ├── start_rag_server.sh        # Startup script (NEW)
│   ├── rag_inference_groq.py      # Original CLI script
│   ├── chunks_embed.py            # Embedding generation
│   ├── query_preprocessor.py      # Query preprocessing
│   ├── embeddings.joblib          # Pre-computed embeddings
│   └── requirements.txt           # Python dependencies
└── src/com/lushprojects/circuitjs1/client/
    ├── AIChatbotDialog.java       # Chatbot UI (MODIFIED)
    └── CirSim.java                # Main simulator (MODIFIED)
```

## Next Steps

1. **Improve UI**: Add progress bars, better error messages
2. **Cache responses**: Store common queries
3. **Multi-turn conversations**: Maintain chat context
4. **Circuit validation**: Verify generated circuits before import
5. **User feedback**: Allow users to rate AI responses
6. **Authentication**: Add API key authentication for production

## License

Same as CircuitJS1 - GNU General Public License v2.0
