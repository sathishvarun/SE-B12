#!/usr/bin/env bash
# Quick test of the running API (start it first with: uvicorn api:app --reload)
echo "== Health check =="
curl -s http://127.0.0.1:8000/
echo -e "\n\n== Generate =="
curl -s -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?", "max_new_tokens": 120, "temperature": 0.7}'
echo
