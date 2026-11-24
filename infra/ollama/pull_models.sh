#!/usr/bin/env sh
# Pulls the model named in .env (default qwen3:8b) into the Ollama container.
set -e
MODEL="${OLLAMA_MODEL:-$(grep '^OLLAMA_MODEL=' .env 2>/dev/null | cut -d= -f2)}"
MODEL="${MODEL:-qwen3:8b}"
echo "Pulling $MODEL ..."
docker compose exec ollama ollama pull "$MODEL"
