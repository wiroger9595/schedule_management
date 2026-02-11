from app.services.cloudinary_service import upload_user_photo
import os
from dotenv import load_dotenv

load_dotenv()

def test_upload():
    print(f"Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
    print(f"API Key: {os.getenv('CLOUDINARY_API_KEY')}")
    # Don't print secret
    
    # Create dummy image data (1x1 transparent gif)
    dummy_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    
    try:
        print("Attempting upload...")
        result = upload_user_photo("test_user_123", dummy_data, "test.gif")
        print("Upload Result:", result)
        print(f"Please check if this URL is accessible: {result['url']}")
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    test_upload()
