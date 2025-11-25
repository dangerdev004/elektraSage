import requests
import pandas as pd
import json
import joblib

# Vector embedding using the bge-m3 model of ollama
def vector_embedding(text_array):
    """
    Embed text using Ollama's bge-m3 model
    text_array: list of strings or single string
    """
    # Handle single string
    if isinstance(text_array, str):
        text_array = [text_array]
    
    r = requests.post("http://localhost:11434/api/embed", json={
        "model": "bge-m3",
        "input": text_array
    })
    embeddings = r.json()['embeddings']
    return embeddings

def main():
    print("Loading chunk file...")
    with open('jsons/chunk_file.json') as f:
        chunk_file = json.load(f)
    
    print(f"Found {len(chunk_file['chunks'])} circuits")
    print("Creating embeddings using searchable_text field...")
    
    # Embed the searchable text instead of just the filename
    searchable_texts = [c['searchable_text'] for c in chunk_file['chunks']]
    
    print("Calling Ollama API for embeddings (this may take a moment)...")
    embeddings = vector_embedding(searchable_texts)
    
    print("Creating dataframe...")
    my_dicts = []
    for i, chunk in enumerate(chunk_file['chunks']):
        chunk["chunk_id"] = i
        chunk["embedding"] = embeddings[i]
        my_dicts.append(chunk)
    
    df = pd.DataFrame.from_records(my_dicts)
    
    print("Saving embeddings to embeddings.joblib...")
    joblib.dump(df, "embeddings.joblib")
    
    print(f"\nSuccessfully embedded {len(df)} circuits")
    print(f"Embedding dimension: {len(embeddings[0])}")
    print(f"Dataframe columns: {list(df.columns)}")
    print("Embeddings saved to embeddings.joblib")

if __name__ == "__main__":
    main()