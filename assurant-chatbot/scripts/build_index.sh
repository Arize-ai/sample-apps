#!/bin/bash
# Run this before building the Docker image
cd /path/to/your/project
python -c "
from src.llamaindex_app.index_manager import IndexManager
from src.llamaindex_app.main import init_openai_client
import os

# Ensure we're using the backend storage path
os.environ['STORAGE_DIR'] = './backend/storage'

client = init_openai_client()
manager = IndexManager(openai_client=client)
print('Index built successfully!')
" 