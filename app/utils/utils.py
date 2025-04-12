
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, Optional
from loguru import logger

from app.api.auth import get_api_key
from app.cache.redis import get_cache_key, get_cached_data, set_cached_data
from app.db.models import TaoDividend, User, get_engine
from app.tasks import analyze_sentiment_and_stake

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt
from bson import ObjectId
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from app.schema.schema import UserCreate, UserResponse, Token, TokenData


# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__default_rounds=12,  # Explicitly set bcrypt version
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = os.getenv("API_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password, hashed_password):
    logger.info(f"Verifying password: {plain_password} against {hashed_password}")
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_user_by_username(username: str):
    engine = await get_engine()
    users = await engine.find(User, User.username == username)
    return users[0] if users else None

async def get_user_by_email(email: str):
    engine = await get_engine()
    users = await engine.find(User, User.email == email)
    return users[0] if users else None

async def get_user_by_id(user_id: str):
    try:
        engine = await get_engine()
        obj_id = ObjectId(user_id)
        user = await engine.find_one(User, User.id == obj_id)
        return user
    except:
        return None

async def create_user(user_data: UserCreate):
    # Check if email already exists
    engine = await get_engine()
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        return None
    
    # Check if username already exists
    existing_user = await get_user_by_username(user_data.username)
    if existing_user:
        return None
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    return await engine.save(new_user)


async def authenticate_user(username: str, password: str):
    user = await get_user_by_username(username)
    logger.info(f"User found: {user}")
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        logger.info(f"Password verification failed for user: {username}")
        return False
    logger.info(f"Password verified for user: {username}")
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id)
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

