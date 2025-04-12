# app/utils/config.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv(override=True)


class Settings(BaseSettings):
    """Application settings"""
    
    API_SECRET_KEY: str =os.getenv("API_SECRET_KEY")
    API_TOKEN: str =os.getenv("API_TOKEN")
    DEBUG: bool =True 

    REDIS_HOST: str =os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int =int(os.getenv("REDIS_PORT", 6379))

    MONGODB_URL: str =os.getenv("MONGODB_URL")
    MONGODB_DB: str =os.getenv("MONGODB_DB")

    DATURA_API_KEY: str =os.getenv("DATURA_API_KEY")
    DATURA_API_URL:str =os.getenv("DATURA_API_URL")

    CHUTES_API_KEY: str =os.getenv("CHUTES_API_KEY")
    CHUTES_ID: str =os.getenv("CHUTES_ID")
    CHUTES_API_URL:str =os.getenv("CHUTES_API_URL")
    WALLET_MNEMONIC:str =os.getenv("WALLET_MNEMONIC")
    WALLET_NAME:str =os.getenv("WALLET_NAME")
    WALLET_HOTKEY:str  =os.getenv("WALLET_HOTKEY")

settings = Settings()