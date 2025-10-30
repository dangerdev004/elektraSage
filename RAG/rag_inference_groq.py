import chunks_embed
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import numpy as np
import os
from groq import Groq

# Retriving the Groq API key that is stored in environment variable 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Load the saved embedded data for checking similarities with the query
df = joblib.load("embeddings.joblib")

incomming_query = input("Ask a Question: ")
print("Vector Embedding of query...")
query_embedded = chunks_embed.vector_embedding(incomming_query)[0]
print("Query successfully vector embedded")

# Cosine similarity checking
similarities = cosine_similarity(np.vstack(df["embedding"]), [query_embedded]).flatten()

# Consider only the top 7 which has the highest cosine_similarity values
top_result = 7
max_indx = similarities.argsort()[::-1][0:top_result]

# Storing the Circuit name, index and circuit text as a string
new_df = df.loc[max_indx]
full_text = ""
for idx, row in new_df.iterrows():
    full_text += f"\nIndex: {idx} | Circuit Name: {row['name']}\nCircuit text:\n{row['text']}\n"


# Prompt for the LLM
prompt = f"""
You are a **RAG-based Circuit Simulator** built using Falstad circuit text files.

Below are the top retrieved results from the RAG system, with the first entry having the highest priority:
{full_text}

================ USER QUERY ================
{incomming_query}

================ INSTRUCTIONS ================
1. If the user provides **circuit specifications or parameter values**, update the corresponding parameter values in the RAG-generated Falstad circuit text **so that the circuit behaves according to the user’s request**.  
   - Do NOT modify the circuit’s components, layout coordinates, or topology. Only update the parameter values.

2. If the user does **not** provide any specific parameters, simply return the original RAG-generated circuit text.

3. If the user asks a **non-circuit-related** question, do NOT answer it. Instead, politely respond that only circuit design–related questions are supported.

4. Absolutely do NOT:
   - Mention that this system uses RAG, retrievals, cosine similarity, ranking methods, or any internal process.
   - Reveal intermediate reasoning steps, model details, or source text origins.
   - Generate or "hallucinate" new circuits that are not part of the RAG results.

================ OUTPUT FORMAT ================
Return **only**:
- The final Falstad circuit text (after modifications, if applicable), and  
- A concise, relevant answer if the user’s question is related to circuits or electronics.
"""


# Storing the prompt to a text file
with open('prompt.txt', 'w')as f:
    f.write(prompt)

# Giving the prompt to groq
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)
chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt,
        }
    ],
    model="llama-3.3-70b-versatile",
)

# Printing the response from Groq
print(30*"=")
print(chat_completion.choices[0].message.content)
print(30*"=")
