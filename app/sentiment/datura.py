import os
import httpx
from typing import List, Dict, Any, Optional
from loguru import logger

# Datura.ai API configuration
DATURA_API_KEY = os.getenv("DATURA_API_KEY")
DATURA_API_URL = "https://api.datura.ai/api/v1"

async def search_twitter(netuid: int, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search recent tweets about the specified subnet.
    
    Args:
        netuid: Subnet ID to search for
        max_results: Maximum number of tweets to return
        
    Returns:
        List of tweets with content and metadata
    """
    if not DATURA_API_KEY:
        logger.error("Datura API key not found")
        raise ValueError("Datura API key not configured")
    
    search_term = f"Bittensor netuid {netuid}"
    
    # Build request
    url = f"{DATURA_API_URL}/twitter/search"
    headers = {
        "Authorization": f"Bearer {DATURA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": search_term,
        "max_results": max_results,
        "tweet_fields": ["created_at", "public_metrics", "text"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if data contains tweets
            if "data" not in data or not data["data"]:
                logger.warning(f"No tweets found for search term: {search_term}")
                return []
            
            # Process tweets
            tweets = []
            for tweet in data["data"]:
                tweets.append({
                    "id": tweet.get("id"),
                    "text": tweet.get("text"),
                    "created_at": tweet.get("created_at"),
                    "metrics": tweet.get("public_metrics", {})
                })
            
            logger.info(f"Retrieved {len(tweets)} tweets for subnet {netuid}")
            return tweets
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Datura API HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Datura API request error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error searching Twitter: {str(e)}")
        raise