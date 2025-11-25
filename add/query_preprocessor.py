import requests
import os
from groq import Groq

def extract_keywords_from_query(query, api_key):
    """
    Extract circuit-relevant keywords from user query using LLM.
    Removes parameter values and focuses on circuit type/topology.
    """
    
    extraction_prompt = f"""You are a circuit design assistant. Extract the KEY CIRCUIT CONCEPTS from the user's query.

**USER QUERY:**
{query}

**YOUR TASK:**
Extract ONLY the circuit type, topology, and component keywords. IGNORE all numerical values, parameters, and specifications.

**RULES:**
- Focus on: circuit type, component names, topology, functionality
- Remove: voltage values, current values, resistance values, all numbers with units
- Extract: what type of circuit, what components, what configuration
- Keep it concise: 5-15 words maximum

**EXAMPLES:**

Query: "Design a 6-bit R2R ladder DAC"
Keywords: R2R ladder DAC 6-bit digital to analog converter

Query: "using fulladd and halfadd, make a 4-bit ripple carry adder"
Keywords: full adder half adder ripple carry adder 4-bit arithmetic

Query: "Design a voltage divider with source resistance using a single power supply 10V for the following specifications Vt = 0.5V, Id = 2mA, Vds = 50% of Vdd, kn = 100uA/v^2"
Keywords: voltage divider source resistance power supply MOSFET bias circuit

Query: "Create an 8-bit binary counter with reset"
Keywords: binary counter 8-bit counter reset sequential logic

Query: "Build a bandpass filter with cutoff frequencies 1kHz and 5kHz using op-amp"
Keywords: bandpass filter op-amp active filter

Query: "Design a common emitter amplifier with voltage gain of 50"
Keywords: common emitter amplifier BJT transistor amplifier

Now extract keywords from the user's query. Respond with ONLY the keywords, no explanations:"""

    try:
        client = Groq(api_key=api_key)
        
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": extraction_prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=100,
        )
        
        keywords = completion.choices[0].message.content.strip()
        return keywords
    
    except Exception as e:
        print(f"Warning: Keyword extraction failed ({e}), using original query")
        return query


def preprocess_query(query, api_key):
    """
    Preprocess user query by extracting keywords for better retrieval.
    Returns both original query and extracted keywords.
    """
    print("Extracting keywords from query...")
    keywords = extract_keywords_from_query(query, api_key)
    print(f"Extracted keywords: {keywords}")
    return keywords