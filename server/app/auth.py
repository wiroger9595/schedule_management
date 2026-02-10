from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.database import get_session
from app.models.user import User
from app.redis_client import get_redis
from pydantic import BaseModel
import os
import uuid

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-keep-it-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str

class OAuthData(BaseModel):
    sub: str
    email: str
    name: str | None = None
    id_token: str | None = None
    identityToken: str | None = None

def verify_password(plain_password, password):
    return pwd_context.verify(plain_password, password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session), redis=Depends(get_redis)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is in Redis (whitelist/session approach)
    is_valid = await redis.get(f"token:{token}")
    if not is_valid:
         raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_session), redis=Depends(get_redis)):
    # Check if user exists
    statement = select(User).where(User.email == user_data.email)
    result = await session.execute(statement)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    pwd = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email, 
        hashed_password=pwd,
        full_name=user_data.full_name
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    # Generate Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    
    # Store token in Redis
    await redis.setex(f"token:{access_token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "valid")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session), redis=Depends(get_redis)):
    statement = select(User).where(User.email == form_data.username)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Store token in Redis
    await redis.setex(f"token:{access_token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "valid")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/google", response_model=Token)
async def google_auth(oauth_data: OAuthData, session: AsyncSession = Depends(get_session), redis=Depends(get_redis)):
    """Google OAuth login/register"""
    # In production, verify the id_token with Google
    # For now, we trust the client-provided data
    
    # Check if user exists by email
    statement = select(User).where(User.email == oauth_data.email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            email=oauth_data.email,
            hashed_password="",  # No password for OAuth users
            full_name=oauth_data.name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    # Generate Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Store token in Redis
    await redis.setex(f"token:{access_token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "valid")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/apple", response_model=Token)
async def apple_auth(oauth_data: OAuthData, session: AsyncSession = Depends(get_session), redis=Depends(get_redis)):
    """Apple Sign In login/register"""
    # In production, verify the identityToken with Apple
    # For now, we trust the client-provided data
    
    # Check if user exists by email
    statement = select(User).where(User.email == oauth_data.email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            email=oauth_data.email,
            hashed_password="",  # No password for OAuth users
            full_name=oauth_data.name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    # Generate Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Store token in Redis
    await redis.setex(f"token:{access_token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "valid")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme), redis=Depends(get_redis)):
    await redis.delete(f"token:{token}")
    return {"message": "Successfully logged out"}
