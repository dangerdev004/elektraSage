#!/bin/bash
set -e

echo "Starting CircuitJS..."
./dev.sh start &

echo "Starting SPICE API..."
(cd /src/spice_ui && npm run server) &

echo "Starting SPICE UI..."
(cd /src/spice_ui && npm run dev -- --host 0.0.0.0) &

echo "Starting RAG server..."
exec python add/app.py
