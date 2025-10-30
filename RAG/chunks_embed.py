import requests
import pandas as pd
import json
import joblib

# Vector embedding using the bge-m3 model of ollama
def vector_embedding(text_array):
    r = requests.post("http://localhost:11434/api/embed", json={
        "model": "bge-m3",
        "input": text_array
    })
    embeddings = r.json()['embeddings']
    return embeddings

def main():
    with open ('jsons/chunk_file.json') as f:
        chunk_file = json.load(f)
    embeddings = vector_embedding([c['name'] for c in chunk_file['chunks']])

    my_dicts = []
    for i, chunk in enumerate(chunk_file['chunks']):
        chunk["chunk_id"] = i
        chunk["embedding"] = embeddings[i]
        my_dicts.append(chunk)

    df = pd.DataFrame.from_records(my_dicts)
    joblib.dump(df, "embeddings.joblib")
    print("Dataframe Successfully Dumped")

if __name__ == "__main__":
    main()
