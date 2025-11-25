import os
import json
from circuit_metadata import get_circuit_metadata

circuit_files = os.listdir("circuits")
circuit_files = sorted(circuit_files)
os.makedirs('jsons', exist_ok=True)

print(f"Processing {len(circuit_files)} circuit files...")

chunks = []
for file in circuit_files:
    filename = file[:-4] 
    print(f"Processing: {filename}")
    
    with open(f"circuits/{file}") as f:
        text = f.read()
    
    metadata = get_circuit_metadata(filename)
    
    searchable_text = f"{metadata['name']} {metadata['description']} {' '.join(metadata['keywords'])}"
    
    data = {
        'filename': filename,
        'name': metadata['name'],
        'description': metadata['description'],
        'category': metadata['category'],
        'keywords': metadata['keywords'],
        'text': text,
        'searchable_text': searchable_text
    }
    chunks.append(data)

with open("jsons/chunk_file.json", "w") as f:
    json.dump({'chunks': chunks}, f, indent=2)

print(f"\nSuccessfully created chunk_file.json with {len(chunks)} circuits")
print("Each circuit now has: name, description, category, keywords, and searchable_text")
