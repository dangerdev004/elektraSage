import chunks_embed
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import numpy as np
import os
from groq import Groq
from query_preprocessor import preprocess_query

# Retrieve the Groq API key from environment variable
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Load the saved embedded data
print("Loading embeddings...")
df = joblib.load("embeddings.joblib")

# Get user query
incoming_query = input("Ask a Question: ")
print(f"\nOriginal query: {incoming_query}")

# Extract keywords for better retrieval
query_keywords = preprocess_query(incoming_query, GROQ_API_KEY)

# Embed the KEYWORDS instead of the full query
print("\nVector embedding of keywords...")
query_embedded = chunks_embed.vector_embedding(query_keywords)[0]
print("Keywords successfully vector embedded")

# Cosine similarity checking
print("Computing similarities...")
similarities = cosine_similarity(np.vstack(df["embedding"]), [query_embedded]).flatten()

# Consider top 5 results
top_result = 5
max_indx = similarities.argsort()[::-1][0:top_result]

# Format the retrieved circuits with rich metadata
new_df = df.loc[max_indx]
circuit_context = ""

print(f"\nTop {top_result} relevant circuits found:")
for idx, row in new_df.iterrows():
    print(f"  {row['name']} (similarity: {similarities[idx]:.3f})")
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


prompt = f"""
You are a **RAG-based Circuit Simulator** using Falstad circuit text files. The base circuit text retrieve is provided below:  
{circuit_context}

================ USER QUERY ================
{incoming_query}

The objective is to generate a circuit design based on the user’s specifications while maintaining the integrity of the original circuit design. 

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

The final deliverable should be the updated circuit text based on the user’s specifications without additional explanations.

Make sure to follow these guidelines for clarity:  
- Use proper node connections.
- Ensure no overlapping components.
- Maintain clear spacing between components.
- Adjust component positions based on the original circuit layout.
- Dont cross wires over any component

I want you to provide the finalized circuit text for the user’s query:  
{incoming_query}
"""


try:
    # Save prompt for debugging
    with open('prompt.txt', 'w') as f:
        f.write(prompt)
    print("\nPrompt saved to prompt.txt")
    
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
    if response.startswith("```"):
        lines = response.split('\n')
        response = '\n'.join([l for l in lines if not l.startswith("```")])
    
    # Save response to file
    with open('generated_circuit.txt', 'w') as f:
        f.write(response)
    
    print("\n" + "="*70)
    print("GENERATED CIRCUIT:")
    print("="*70)
    print(response)
    print("="*70)
    print("\nCircuit saved to generated_circuit.txt")
    print("You can import this into Falstad Circuit Simulator")
    
except Exception as e:
    print(f"\nError: {e}")
