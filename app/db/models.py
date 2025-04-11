import os
from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine, Model, Field
from loguru import logger

# MongoDB connection
client = None
engine = None

class TaoDividend(Model):
    """Model for storing Tao dividend data"""
    netuid: int
    hotkey: str
    dividend: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
class SentimentAnalysis(Model):
    """Model for storing sentiment analysis results"""
    netuid: int
    sentiment_score: int
    tweet_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    search_term: str
    
class StakeOperation(Model):
    """Model for storing stake operation history"""
    netuid: int
    hotkey: str
    operation_type: str  # "stake" or "unstake"
    amount: float
    sentiment_score: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    transaction_hash: Optional[str] = None
    successful: bool = False
    error_message: Optional[str] = None

class User(Model):
    """Model for user authentication"""
    email: str = Field(unique=True)
    username: str = Field(unique=True)
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

async def init_db():
    """Initialize database connection"""
    global client, engine
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db = os.getenv("MONGODB_DB", "bittensor_api")
    
    client = AsyncIOMotorClient(mongodb_url)
    # Fixed parameter name from motor_client to client
    engine = AIOEngine(client=client, database=mongodb_db)
    logger.info(f"Connected to MongoDB at {mongodb_url}")
    logger.info(f"Using engine: {engine}")
    
    # Verify connection
    try:
        await client.admin.command('ping')
        print(f"Connected to MongoDB at {mongodb_url}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {str(e)}")

    return engine

async def get_engine():
    """Dependency to get the database engine"""
    if engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_db() first.")
    return engine

async def close_db():
    """Close database connection"""
    global client
    if client:
        client.close()