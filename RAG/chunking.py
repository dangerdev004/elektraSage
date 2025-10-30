import os
import json

circuit_files = os.listdir("falstad-circuit-simulator/circuits")
circuit_files = sorted(circuit_files)

os.makedirs('jsons', exist_ok=True)

print("No. of files", len(circuit_files))

chunks = []
for file in circuit_files:
    print(file)
    with open (f"falstad-circuit-simulator/circuits/{file}") as f:
        text = f.read()
    data = {'name':file[:-4], 'text': text}

    chunks.append(data)
with open ("jsons/chunk_file.json", "w") as f:
    json.dump({'chunks':chunks}, f)
