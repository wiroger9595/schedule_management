import cloudinary
import cloudinary.api
import os
from dotenv import load_dotenv

load_dotenv()

# Configure
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

print(f"Checking Cloudinary: {os.getenv('CLOUDINARY_CLOUD_NAME')}")

try:
    print("\nListing resources in 'user-photo/' folder...")
    # Note: listing via API requires Admin API access usually, or signed requests.
    # standard uploader doesn't list. We need 'cloudinary.api' which uses the API Key/Secret.
    
    result = cloudinary.api.resources(
        type="upload",
        prefix="user-photo", # removed trailing slash just in case
        max_results=50
    )
    
    resources = result.get('resources', [])
    if not resources:
        print("No resources found matching prefix 'user-photo'")
    else:
        print(f"Found {len(resources)} resources:")
        for res in resources:
            print(f"- {res['public_id']} | {res['secure_url']}")

except Exception as e:
    print(f"\n--- Error listing resources ---")
    print(e)
