#!/usr/bin/env python3
"""Test which HuggingFace models work with chat_completion."""

import os
from dotenv import load_dotenv
load_dotenv('server/.env-stage')

from huggingface_hub import InferenceClient

hf_key = os.getenv("HUGGINGFACE_API_KEY")
client = InferenceClient(api_key=hf_key)

models_to_test = [
    "meta-llama/Llama-3.2-3B-Instruct",
    "meta-llama/Meta-Llama-3-8B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "google/gemma-2-9b-it",
    "microsoft/Phi-3.5-mini-instruct",
    "HuggingFaceH4/zephyr-7b-beta",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "mistralai/Mistral-Nemo-Instruct-2407",
]

for model in models_to_test:
    try:
        result = client.chat_completion(
            model=model,
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=10,
        )
        print(f"✅ {model}: WORKS")
    except Exception as e:
        msg = str(e)[:120]
        print(f"❌ {model}: {msg}")
