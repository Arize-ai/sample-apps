#!/bin/bash
# Run this before building the Docker image

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Use python3 explicitly
python3 -c "
from src.llamaindex_app.index_manager import IndexManager
from src.llamaindex_app.main import init_openai_client
import os

# Ensure we're using the backend storage path
os.environ['STORAGE_DIR'] = './backend/storage'

client = init_openai_client()
manager = IndexManager(openai_client=client)
print('Index built successfully!')
" 