from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import jwt
import os
from loguru import logger

# API token header setup
API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

SECRET_KEY = os.getenv("API_SECRET_KEY")
ALGORITHM = "HS256"


async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate JWT token from the Authorization header.
    Expects format: "Bearer <token>"
    """
    if not api_key_header:
        logger.warning("Authorization header is missing")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Authorization header missing"
        )
    
    parts = api_key_header.split()
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization header format: {api_key_header}")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, 
            detail="Authorization header must be in the format 'Bearer <token>'"
        )
    
    token = parts[1]
    
    try:
        # Decode and validate the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Token validated successfully: {payload}")
        return payload  # Return the decoded payload for further use
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Invalid token"
        )