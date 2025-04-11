from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, Optional
from loguru import logger

from app.api.auth import get_api_key
from app.cache.redis import get_cache_key, get_cached_data, set_cached_data
from app.blockchain.subtensor import get_tao_dividends_per_subnet
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
from app.utils.utils import create_access_token, authenticate_user, create_user, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/v1", tags=["Bittensor API"])

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    try:
        new_user = await create_user(user)
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        
        # Convert to response model
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "username": new_user.username,
            "is_admin": new_user.is_admin,
            "created_at": new_user.created_at
        }
    except Exception as e:
        logger.error(f"Error in user registration: {str(e)}")

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = await authenticate_user(form_data.username, form_data.password)
        logger.info(f"User authenticated: {user}")
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token, expires_at = create_access_token(
            data={"sub": user.username, "id": str(user.id)},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_at": expires_at
        }
    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/tao_dividends")
async def get_tao_dividends(
    netuid: Optional[int] = Query(None, description="Subnet ID"),
    hotkey: Optional[str] = Query(None, description="Hotkey address"),
    trade: bool = Query(False, description="Whether to trigger stake/unstake based on sentiment"),
    api_key: str = Depends(get_api_key)
):
    """
    Get Tao dividends for a subnet and hotkey.
    
    If netuid is omitted, returns data for all netuids.
    If hotkey is omitted, returns data for all hotkeys on the specified netuid.
    If trade=True, triggers sentiment analysis and stake/unstake in the background.
    """
    try:
        # Check cache first
        engine = await get_engine()
        cache_key = await get_cache_key(netuid, hotkey)
        cached_data = await get_cached_data(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for {cache_key}")
            result = cached_data
            result["cached"] = True
        else:
            logger.info(f"Cache miss for {cache_key}, querying blockchain")
            logger.info(f"Fetching dividends for netuid={netuid}, hotkey={hotkey}")
            dividend = await get_tao_dividends_per_subnet(netuid, hotkey)

            result = {
                "netuid": netuid,
                "hotkey": hotkey,
                "dividend": dividend,
                "timestamp": str(datetime.now())
            }

            logger.info(f"Dividends fetched: {result}")
            logger.info(f"Dividends fetched: {result}")
            result["cached"] = False
            
            # Store in cache
            await set_cached_data(cache_key, result)
            logger.info(f"Stored data in cache with key: {cache_key}")
            # Store in database
            if netuid is not None and hotkey is not None:
                dividend_record = TaoDividend(
                    netuid=netuid,
                    hotkey=hotkey,
                    dividend=result['dividend']
                )
                await engine.save(dividend_record)

            logger.info(f"Stored dividend record in database: {dividend_record}")
        
        # Handle trade parameter (sentiment analysis and stake/unstake)
        if trade:
            # Use default values if netuid or hotkey is None
            stake_netuid = netuid if netuid is not None else 18
            stake_hotkey = hotkey if hotkey is not None else "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v"
            
            # Trigger background task
            logger.info(f"Triggering sentiment analysis and stake for netuid={stake_netuid}, hotkey={stake_hotkey}")
            analyze_sentiment_and_stake.delay(stake_netuid, stake_hotkey)
            
            result["stake_tx_triggered"] = True
        else:
            result["stake_tx_triggered"] = False
        
        return result
        
    except Exception as e:
        logger.error(f"Error in tao_dividends endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/operations")
async def get_operations(
    netuid: Optional[int] = Query(None, description="Filter by subnet ID"),
    hotkey: Optional[str] = Query(None, description="Filter by hotkey address"),
    api_key: str = Depends(get_api_key)
):
    """
    Get history of stake operations.
    Can be filtered by netuid and/or hotkey.
    """
    try:
        from app.db.models import StakeOperation
        engine = await get_engine()
        # Build query
        query = {}
        if netuid is not None:
            query["netuid"] = netuid
        if hotkey is not None:
            query["hotkey"] = hotkey
        
        # Retrieve operations from database
        operations = await engine.find(StakeOperation, query)
        
        return {
            "operations": [op.dict() for op in operations]
        }
        
    except Exception as e:
        logger.error(f"Error in operations endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sentiment")
async def get_sentiment(
    netuid: int = Query(..., description="Subnet ID"),
    api_key: str = Depends(get_api_key)
):
    """
    Get historical sentiment analysis for a subnet.
    """
    try:
        from app.db.models import SentimentAnalysis
        engine = await get_engine()
        # Retrieve sentiment records from database
        sentiment_records = await engine.find(SentimentAnalysis, SentimentAnalysis.netuid == netuid)
        
        return {
            "sentiment_history": [record.dict() for record in sentiment_records]
        }
        
    except Exception as e:
        logger.error(f"Error in sentiment endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")