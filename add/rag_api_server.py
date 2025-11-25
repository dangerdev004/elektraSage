"""
Flask API Server for RAG-based Circuit Generation
Wraps the rag_inference_groq.py logic as a REST API endpoint
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import chunks_embed
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import numpy as np
import os
from groq import Groq
from query_preprocessor import preprocess_query
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for browser access

# Retrieve the Groq API key from environment variable
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Load the saved embedded data at startup
print("Loading embeddings...")
try:
    df = joblib.load("embeddings.joblib")
    print(f"Embeddings loaded successfully. {len(df)} circuits available.")
except Exception as e:
    print(f"Error loading embeddings: {e}")
    df = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "embeddings_loaded": df is not None,
        "circuits_available": len(df) if df is not None else 0
    })

@app.route('/query', methods=['POST'])
def query_circuit():
    """
    Main RAG query endpoint
    Expects JSON: {"query": "user question"}
    Returns JSON: {"success": bool, "response": str, "circuit_text": str, "error": str}
    """
    try:
        # Validate request
        if not request.json or 'query' not in request.json:
            return jsonify({
                "success": False,
                "error": "Missing 'query' field in request body"
            }), 400
        
        incoming_query = request.json['query'].strip()
        
        if not incoming_query:
            return jsonify({
                "success": False,
                "error": "Query cannot be empty"
            }), 400
        
        if df is None:
            return jsonify({
                "success": False,
                "error": "Embeddings not loaded. Please check server startup logs."
            }), 500
        
        print(f"\n{'='*70}")
        print(f"Received query: {incoming_query}")
        print(f"{'='*70}")
        
        # Extract keywords for better retrieval
        print("Preprocessing query...")
        query_keywords = preprocess_query(incoming_query, GROQ_API_KEY)
        print(f"Extracted keywords: {query_keywords}")
        
        # Embed the KEYWORDS instead of the full query
        print("Vector embedding keywords...")
        query_embedded = chunks_embed.vector_embedding(query_keywords)[0]
        
        # Cosine similarity checking
        print("Computing similarities...")
        similarities = cosine_similarity(np.vstack(df["embedding"]), [query_embedded]).flatten()
        
        # Consider top 5 results
        top_result = 5
        max_indx = similarities.argsort()[::-1][0:top_result]
        
        # Format the retrieved circuits with rich metadata
        new_df = df.loc[max_indx]
        circuit_context = ""
        
        print(f"\nTop {top_result} relevant circuits:")
        retrieved_circuits = []
        for idx, row in new_df.iterrows():
            similarity_score = similarities[idx]
            print(f"  {row['name']} (similarity: {similarity_score:.3f})")
            retrieved_circuits.append({
                "name": row['name'],
                "similarity": float(similarity_score)
            })
            
            circuit_context += f"""
{'='*70}
INDEX: {idx}
CIRCUIT NAME: {row['name']}
DESCRIPTION: {row['description']}
CATEGORY: {row['category']}
KEYWORDS: {', '.join(row['keywords'])}
{'='*70}
CIRCUIT TEXT:
{row['text']}

"""
        
        # Build the prompt
        prompt = f"""
You are a **RAG-based Circuit Simulator** using Falstad circuit text files. The base circuit text retrieve is provided below:  
{circuit_context}

================ USER QUERY ================
{incoming_query}

The objective is to generate a circuit design based on the user's specifications while maintaining the integrity of the original circuit design. 

You have to follow these steps:  
1. Analyze the provided base circuit text thoroughly.  
2. If the user request is simply to present the circuit without specifying changes, and if it matches the base circuit design, return the base circuit text as is.  
3. If the user requests an extension or reduction of the base circuit, adjust the circuit accordingly while ensuring that:
   - All components remain connected and coherent.
   - Adjust component placements based on the base circuit's canvas logic, ensuring no components overlap and that there are no disconnections.
   - Maintain the original design flow; do not alter the fundamental circuit topology unless explicitly requested. 
   - Properly space out the components for clarity and create appropriate junction nodes where wires branch out.
   - Ensure that proper power supply or ground connections are established for any new components added.

Avoid any hallucination, and focus on providing accurate and well-structured circuit text. 

The final deliverable should be the updated circuit text based on the user's specifications without additional explanations.

Make sure to follow these guidelines for clarity:  
- Use proper node connections.
- Ensure no overlapping components.
- Maintain clear spacing between components.
- Adjust component positions based on the original circuit layout.
- Dont cross wires over any component

I want you to provide the finalized circuit text for the user's query:  
{incoming_query}
"""
        
        # Call Groq API
        print("Calling Groq API for circuit generation...")
        client = Groq(api_key=GROQ_API_KEY)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=8000,
        )
        
        # Get response
        response = chat_completion.choices[0].message.content
        
        # Clean response (remove markdown if present)
        response = response.strip()
        circuit_text = response
        if response.startswith("```"):
            lines = response.split('\n')
            circuit_text = '\n'.join([l for l in lines if not l.startswith("```")])
        
        print("\n" + "="*70)
        print("CIRCUIT GENERATED SUCCESSFULLY")
        print("="*70)
        
        return jsonify({
            "success": True,
            "response": "Circuit generated successfully! You can import it into the simulator.",
            "circuit_text": circuit_text,
            "retrieved_circuits": retrieved_circuits,
            "keywords": query_keywords
        })
        
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"\nError processing query: {error_msg}")
        print(error_trace)
        
        return jsonify({
            "success": False,
            "error": error_msg,
            "trace": error_trace if app.debug else None
        }), 500

@app.route('/simple-query', methods=['POST'])
def simple_query():
    """
    Simplified query endpoint for basic circuit questions (no generation)
    Expects JSON: {"query": "user question"}
    Returns JSON: {"success": bool, "response": str}
    """
    try:
        if not request.json or 'query' not in request.json:
            return jsonify({
                "success": False,
                "error": "Missing 'query' field in request body"
            }), 400
        
        incoming_query = request.json['query'].strip()
        
        if not incoming_query:
            return jsonify({
                "success": False,
                "error": "Query cannot be empty"
            }), 400
        
        # For simple questions, just use Groq directly without RAG
        print(f"Simple query: {incoming_query}")
        
        client = Groq(api_key=GROQ_API_KEY)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful circuit design assistant. Provide clear, concise answers about electronics and circuit design."
                },
                {
                    "role": "user",
                    "content": incoming_query,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=500,
        )
        
        response = chat_completion.choices[0].message.content
        
        return jsonify({
            "success": True,
            "response": response
        })
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error processing simple query: {error_msg}")
        
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

if __name__ == '__main__':
    if not GROQ_API_KEY:
        print("WARNING: GROQ_API_KEY not set in environment variables!")
        print("Please set it with: export GROQ_API_KEY='your-key-here'")
    
    print("\n" + "="*70)
    print("RAG API Server Starting...")
    print("="*70)
    print("Endpoints:")
    print("  GET  /health        - Health check")
    print("  POST /query         - Generate circuit from query (RAG)")
    print("  POST /simple-query  - Answer simple questions (no RAG)")
    print("="*70 + "\n")
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=True)
