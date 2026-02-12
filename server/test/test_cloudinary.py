import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

# Configure
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

print(f"Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
print(f"API Key: {os.getenv('CLOUDINARY_API_KEY')}")

# Create a dummy image file
with open("test_image.txt", "wb") as f:
    f.write(b"fake image content")

try:
    print("Attempting upload...")
    # Using 'raw' resource type for text file, or we can use a real image if we had one.
    # But to test credentials, any upload is fine.
    # Let's try to upload specific content as a 'raw' file to avoid image validation errors if it's not a real image.
    # wait, the code uses resource_type="image". I should try to upload a tiny valid image bytes.
    
    # 1x1 transparent GIF
    small_gif = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    
    response = cloudinary.uploader.upload(
        small_gif,
        public_id="test_upload_debug",
        resource_type="image",
        overwrite=True
    )
    
    print("\n--- Upload Success ---")
    print(f"Public ID: {response.get('public_id')}")
    print(f"URL: {response.get('secure_url')}")
    print(f"Format: {response.get('format')}")
    
except Exception as e:
    print(f"\n--- Upload Failed ---")
    print(e)
