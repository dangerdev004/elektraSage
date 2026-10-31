#!/bin/bash
set -e

echo "Starting CircuitJS..."
./dev.sh start &

echo "Starting RAG server..."
exec python add/app.py
