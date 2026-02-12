import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Test different model names
model_names = [
    "gemini-1.5-flash",
    "models/gemini-1.5-flash",
    "gemini-2.0-flash-exp",
    "models/gemini-2.0-flash-exp"
]

for model in model_names:
    try:
        print(f"Testing model: {model}")
        response = client.models.generate_content(
            model=model,
            contents="Say hello in one word"
        )
        print(f"✓ {model} works! Response: {response.text[:50]}")
        break
    except Exception as e:
        print(f"✗ {model} failed: {str(e)[:100]}")
