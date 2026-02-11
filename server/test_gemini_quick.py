import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

test_prompt = "用繁體中文說 hello"

print("Testing Gemini 2.5 Flash model...")
try:
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=test_prompt
    )
    print(f"✓ Success! Response: {response.text}")
except Exception as e:
    print(f"✗ Error: {e}")
