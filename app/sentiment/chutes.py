import os
import httpx
from typing import List, Dict, Any, Optional
from loguru import logger

# Chutes.ai API configuration
CHUTES_API_KEY = os.getenv("CHUTES_API_KEY")
CHUTES_API_URL = "https://api.chutes.ai/api/v1"
CHUTES_ID = "20acffc0-0c5f-58e3-97af-21fc0b261ec4"  

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
    
    # Combine tweet text for analysis
    combined_text = "\n\n".join([tweet.get("text", "") for tweet in tweets])
    
    # Build request
    url = f"{CHUTES_API_URL}/chutes/{CHUTES_ID}/run"
    headers = {
        "Authorization": f"Bearer {CHUTES_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": {
            "tweet_text": combined_text
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract sentiment score from response
            # Assuming the Chutes.ai LLM returns a sentiment score between -100 and 100
            if "outputs" in data and "sentiment_score" in data["outputs"]:
                sentiment_score = int(data["outputs"]["sentiment_score"])
                logger.info(f"Sentiment analysis complete. Score: {sentiment_score}")
                return sentiment_score
            
            # If output format is different, process accordingly
            # This is an example - adjust based on actual Chutes.ai API response
            if "outputs" in data and "text" in data["outputs"]:
                text_response = data["outputs"]["text"]
                
                # Extract score from text response
                try:
                    # Assuming response contains a number between -100 and 100
                    import re
                    score_match = re.search(r"[-+]?\d+", text_response)
                    if score_match:
                        sentiment_score = int(score_match.group())
                        # Ensure score is within range
                        sentiment_score = max(-100, min(100, sentiment_score))
                        return sentiment_score
                except Exception as e:
                    logger.error(f"Error extracting sentiment score: {str(e)}")
            
            # If no clear score, return 0 (neutral)
            logger.warning("Could not extract sentiment score, defaulting to neutral (0)")
            return 0
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Chutes API HTTP error: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Chutes API request error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise