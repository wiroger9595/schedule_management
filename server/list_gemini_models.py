import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing available models...")
try:
    models = client.models.list()
    print(f"\nFound {len(list(models))} models")
    
    # List again and print details
    for model in client.models.list():
        print(f"\nModel: {model.name}")
        print(f"  Display Name: {model.display_name if hasattr(model, 'display_name') else 'N/A'}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"  Supported methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
