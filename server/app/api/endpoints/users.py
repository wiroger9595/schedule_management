from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlmodel import Session
from ...db.database import get_session
from ...models.user import User
from ...repositories.user_repository import UserRepository
from .auth import get_current_user
from datetime import datetime

router = APIRouter()

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me/profile_picture")
def update_profile_picture(data: dict, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = UserRepository(session)
    image_url = data.get("image_url")
    if not image_url:
        # handle error or specific logic
        pass
        
    current_user.profile_image_path = image_url
    current_user.profile_image_path = image_url
    return repo.update(current_user)

@router.patch("/me")
def update_user_me(data: dict, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = UserRepository(session)
    
    if "full_name" in data:
        current_user.full_name = data["full_name"]
    if "phone" in data:
        current_user.phone = data["phone"]
    if "email" in data:
        current_user.email = data["email"]
    if "line_id" in data:
        current_user.line_id = data["line_id"]
    if "language" in data:
        current_user.language = data["language"]
        
    return repo.update(current_user)

@router.put("/{user_id}")
def update_user_profile(user_id: str, data: dict, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # Basic check
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    repo = UserRepository(session)
    
    # Update allowed fields
    if "full_name" in data:
        current_user.full_name = data["full_name"]
    if "phone" in data:
        current_user.phone = data["phone"]
    if "email" in data:
        current_user.email = data["email"]
    if "line_id" in data:
        current_user.line_id = data["line_id"]
    if "language" in data:
        current_user.language = data["language"]
        
    return repo.update(current_user)

@router.post("/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """上傳用戶頭像到 Cloudinary"""
    from ...services.cloudinary_service import upload_user_photo, delete_user_photo
    
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="只支援 JPG/PNG 格式")
    
    file_data = await file.read()
    
    try:
        repo = UserRepository(session)
        if current_user.public_id:
            # Now we store full public_id, so we can use it directly
            # Fallback for old records if necessary (checking if it looks like a full path)
            old_id = current_user.public_id
            if "/" not in old_id:
                # Legacy support: if we only have filename, assume old path structure
                old_id = f"user-photo/{current_user.user_id}/{old_id}"
            
            delete_user_photo(old_id)

        result = upload_user_photo(
            str(current_user.user_id),
            file_data,
            file.filename
        )
        
        current_user.profile_image_path = result['url']
        current_user.public_id = result['public_id'] # Store full public_id
        current_user.updated_at = datetime.now()
        
        repo.update(current_user)
        
        return {"photo_url": result['url'], "message": "頭像上傳成功"}
    except Exception as e:
        print(f"Error uploading photo: {e}")
        raise HTTPException(status_code=500, detail=f"上傳失敗：{str(e)}")
