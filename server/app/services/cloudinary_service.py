import cloudinary
import cloudinary.uploader
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_user_photo(user_id: str, file_data: bytes, filename: str) -> dict:
    """
    上傳用戶頭像到 Cloudinary
    
    Args:
        user_id: 用戶 ID
        file_data: 圖片資料（bytes）
        filename: 原始檔案名稱
    
    Returns:
        dict with 'url' and 'public_id'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    public_id = f"home/user-photo/{user_id}/{timestamp}"
    
    result = cloudinary.uploader.upload(
        file_data,
        public_id=public_id,
        overwrite=True,
        resource_type="image"
        # folder="user-photo"  <-- Removed to prevent double nesting
    )
    
    # Extract filename from public_id for DB storage
    # Cloudinary public_id matches what we sent: "user-photo/{user_id}/{timestamp}"
    stored_filename = f"{timestamp}.jpg" # Simplified, or extract from result
    
    return {
        'url': result['secure_url'],
        'public_id': result['public_id'], # Full ID for immediate use
        'filename': f"{timestamp}" # Just the filename part
    }

def delete_user_photo(public_id: str) -> bool:
    """
    從 Cloudinary 刪除用戶頭像
    
    Args:
        public_id: Cloudinary public_id
    
    Returns:
        True if successful
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        return result.get('result') == 'ok'
    except Exception as e:
        logger.info(f"Error deleting photo: {e}")
        return False
