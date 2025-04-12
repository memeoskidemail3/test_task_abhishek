import os
import httpx
from typing import List, Dict, Any
from loguru import logger
from app.utils.config import settings

# Datura.ai API configuration
DATURA_API_KEY = settings.DATURA_API_KEY
DATURA_API_URL = settings.DATURA_API_URL


async def search_twitter(netuid: int, count: int = 10) -> List[Dict[str, Any]]:
    """
    Search recent tweets for the specified Bittensor subnet using Datura.ai.

    Args:
        netuid: Subnet ID to search
        count: Max number of tweets to return

    Returns:
        List of tweet dicts with text and metadata
    """
    if not DATURA_API_KEY:
        logger.error("Datura API key not found")
        raise ValueError("Datura API key not configured")

    search_term = f"Bittensor netuid {netuid}"
    logger.info(f"Searching tweets for: {search_term}")

    url = f"{DATURA_API_URL}/twitter"
    headers = {
        "Authorization": DATURA_API_KEY,
        "Content-Type": "application/json"
    }

    params = {
        "query": search_term,
        "blue_verified": False,
        "end_date": "2025-02-17",
        "is_image": False,
        "is_quote": False,
        "is_video": False,
        "lang": "en",
        "min_likes": 0,
        "min_replies": 0,
        "min_retweets": 0,
        "sort": "Top",
        "start_date": "2025-02-16",
        "count": count
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(f"No tweets found for netuid {netuid}")
                return []

            logger.info(f"Fetched tweets for netuid={netuid}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Datura API HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Datura API request error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise