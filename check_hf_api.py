#!/usr/bin/env python3
"""Check HuggingFace InferenceClient API methods."""

from huggingface_hub import InferenceClient

client = InferenceClient(api_key="test_key")

# List available methods
methods = [m for m in dir(client) if not m.startswith('_')]
print("Available HuggingFace InferenceClient methods:")
for m in sorted(methods):
    print(f"  - {m}")
