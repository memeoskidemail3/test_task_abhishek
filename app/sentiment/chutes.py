import os
import httpx
import re
from typing import List, Dict, Any
from loguru import logger
from app.utils.config import settings
import json

from app.utils.config import settings


WALLET_NAME=settings.WALLET_NAME
WALLET_HOTKEY=settings.WALLET_HOTKEY

# Chutes.ai API configuration
CHUTES_API_KEY = settings.CHUTES_API_KEY
CHUTES_API_URL = settings.CHUTES_API_URL



def extract_sentiment_score(response: dict) -> int:
    """
    Safely extract sentiment_score from Chutes.ai response.
    Supports structured JSON, embedded JSON in strings, or raw score in text.
    """
    try:
        # 1. Try structured access (ideal case)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, dict) and "sentiment_score" in content:
            return int(content["sentiment_score"])
        
        # 2. Try parsing embedded JSON in string content
        json_match = re.search(r'\{.*?"sentiment_score"\s*:\s*-?\d+.*?\}', content)
        if json_match:
            try:
                sentiment_data = json.loads(json_match.group())
                return int(sentiment_data.get("sentiment_score", 0))
            except json.JSONDecodeError:
                pass
        
        # 3. Try extracting just a number from anywhere in the content
        score_match = re.search(r"sentiment_score[^0-9\-+]*([-+]?\d+)", content)
        if not score_match:
            score_match = re.search(r"[-+]?\d+", content)
        if score_match:
            score = int(score_match.group())
            return max(-100, min(100, score))  # Clamp to range
        
    except Exception as e:
        print(f"Error extracting sentiment score: {e}")

    # Fallback neutral
    return 0


async def analyze_sentiment(tweets: List[Dict[str, Any]]) -> int:
    """
    Analyze sentiment of tweets using Chutes.ai LLM.

    Args:
        tweets: List of tweet objects with text content

    Returns:
        Sentiment score between -100 (very negative) and +100 (very positive)
    """
    if not CHUTES_API_KEY:
        logger.error("Chutes API key not found")
        raise ValueError("Chutes API key not configured")

    if not tweets:
        logger.warning("No tweets provided for sentiment analysis")
        return 0  # Neutral sentiment if no tweets

    # Combine tweet texts for LLM input
    tweet_lines = "\n\n".join([f"Tweet {i+1}: {t.get('text', '')}" for i, t in enumerate(tweets)])

    # Create prompt for LLM
    prompt = (
        f"Here are some recent tweets about Bittensor netuid.\n\n"
        f"{tweet_lines}\n\n"
        "Analyze the overall sentiment of these tweets and return only a JSON object like:\n"
        '{"sentiment_score": 42}\n'
        "Where sentiment_score ranges from -100 (very negative) to +100 (very positive)."
    )

    # Build request
    url = f"{CHUTES_API_URL}"
    
    headers = {
        "Authorization": f"Bearer {CHUTES_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [
        {
          "role": "user",
          "content": prompt
        }
      ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()

            data = response.json()

            logger.debug(f"Chutes API response: {data}")
            return extract_sentiment_score(data)

    except httpx.HTTPStatusError as e:
        logger.error(f"Chutes API HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Chutes API request error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise