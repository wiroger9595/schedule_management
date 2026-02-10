from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found")
    exit(1)

client = genai.Client(api_key=api_key)

print("--- Testing Generation ---")
try:
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents="Hello, can you hear me?"
    )
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- Listing available models (first 10) ---")
try:
    # helper to print models
    pager = client.models.list(config={'page_size': 10})
    for m in pager:
        print(m.name)
except Exception as e:
    print(f"List models error: {e}")
