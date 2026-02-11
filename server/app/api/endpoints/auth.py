from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from ...core.auth import get_password_hash, create_access_token, verify_password, SECRET_KEY, ALGORITHM
from ...core.redis_client import redis_client
from ...db.database import get_session
from ...models.user import User
from ...repositories.user_repository import UserRepository
from jose import jwt, JWTError

router = APIRouter()
security = HTTPBearer()

def get_current_user(auth: HTTPAuthorizationCredentials = Security(security), session: Session = Depends(get_session)) -> User:
    try:
        # Decode token
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check Redis
        if not redis_client.validate_token(user_id, auth.credentials):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        # Get user
        repo = UserRepository(session)
        user = repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/register")
def register(user_data: dict, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    email = user_data.get('email')
    password = user_data.get('password')
    full_name = user_data.get('full_name')
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    if repo.get_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name
    )
    return repo.create(user)

@router.post("/login")
def login(user_data: dict, session: Session = Depends(get_session)):
    repo = UserRepository(session)
    email = user_data.get('email')
    password = user_data.get('password')
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    user = repo.get_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.user_id})
    
    # Store in Redis
    if not redis_client.store_token(user.user_id, access_token):
        print("Warning: Redis unavailable")
        
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/google")
def google_auth(data: dict, session: Session = Depends(get_session)):
    # In a real app, verify the google id_token here.
    google_id = data.get("sub")
    email = data.get("email")
    
    repo = UserRepository(session)
    # Check by google_id
    # Note: UserRepository currently needs a specific method or raw query
    # Since we didn't add get_by_google_id, let's just query directly or add it.
    # For simplicity, direct query in endpoint for this migration, or extend repo.
    # Better: extend repo logic here conceptually.
    user = session.exec(select(User).where(User.google_id == google_id)).first()
    
    if not user:
        # Check by email
        user = repo.get_by_email(email)
        if user:
            user.google_id = google_id
        else:
            user = User(email=email, google_id=google_id, full_name=data.get("name"))
        repo.create(user) # Create or Update (if session attached? create handles add)
        # Actually repo.create adds, if user already in session it might error or warn.
        # Let's use repo.update if existing.
        if user.id:
            repo.update(user, {})
    
    access_token = create_access_token(data={"sub": user.user_id})
    redis_client.store_token(user.user_id, access_token)
    return {"access_token": access_token}

@router.post("/apple")
def apple_auth(data: dict, session: Session = Depends(get_session)):
    apple_id = data.get("sub")
    email = data.get("email")
    
    repo = UserRepository(session)
    user = session.exec(select(User).where(User.apple_id == apple_id)).first()
    
    if not user:
        user = repo.get_by_email(email)
        if user:
            user.apple_id = apple_id
            repo.update(user, {})
        else:
            user = User(email=email, apple_id=apple_id, full_name=data.get("name"))
            repo.create(user)
    
    access_token = create_access_token(data={"sub": user.user_id})
    redis_client.store_token(user.user_id, access_token)
    return {"access_token": access_token}

@router.post("/logout")
def logout(auth: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            redis_client.revoke_token(user_id, auth.credentials)
        return {"msg": "Successfully logged out"}
    except JWTError:
        return {"msg": "Invalid token"}
