#!/bin/bash

# Install guardrails and specific guards from the hub
python -m pip install --upgrade pip
pip install guardrails-ai
python -m guardrails hub pull DetectJailbreak
python -m guardrails hub pull ToxicLanguage

# Install any other dependencies needed
# pip install other-packages-needed

echo "Setup completed successfully"