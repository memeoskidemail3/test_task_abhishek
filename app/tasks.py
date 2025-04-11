import os
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger

from app.worker import celery_app
from app.sentiment.datura import search_twitter
from app.sentiment.chutes import analyze_sentiment
from app.db.models import SentimentAnalysis, StakeOperation, engine

@celery_app.task(name="app.tasks.analyze_sentiment_and_stake")
def analyze_sentiment_and_stake(netuid: int, hotkey: str):
    """
    Celery task to analyze Twitter sentiment and stake/unstake based on results.
    
    This is a synchronous wrapper around async functions.
    
    Args:
        netuid: Subnet ID
        hotkey: Hotkey address
    """
    logger.info(f"Starting sentiment analysis and stake task for netuid={netuid}, hotkey={hotkey}")
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_analyze_sentiment_and_stake(netuid, hotkey))

async def _analyze_sentiment_and_stake(netuid: int, hotkey: str):
    """
    Async implementation of sentiment analysis and staking/unstaking.
    
    Args:
        netuid: Subnet ID
        hotkey: Hotkey address
        
    Returns:
        Operation result
    """
    try:
        # Search for tweets about the subnet
        tweets = await search_twitter(netuid=netuid)
        
        if not tweets:
            logger.warning(f"No tweets found for subnet {netuid}, skipping sentiment analysis")
            return {
                "success": False,
                "error": "No tweets found for analysis"
            }
        
        # Analyze sentiment
        sentiment_score = await analyze_sentiment(tweets)
        
        # Save sentiment analysis to database
        sentiment_record = SentimentAnalysis(
            netuid=netuid,
            sentiment_score=sentiment_score,
            tweet_count=len(tweets),
            search_term=f"Bittensor netuid {netuid}"
        )
        await engine.save(sentiment_record)
        
        # Calculate stake amount (0.01 tao * sentiment score)
        stake_amount = abs(sentiment_score) * 0.01
        
        # Initialize blockchain client
        client = AsyncBittensorClient()
        await client.initialize()
        
        # Perform stake/unstake operation based on sentiment
        result = None
        if sentiment_score > 0:
            # Positive sentiment - stake
            logger.info(f"Positive sentiment ({sentiment_score}), staking {stake_amount} TAO")
            result = await client.add_stake(netuid, hotkey, stake_amount)
        elif sentiment_score < 0:
            # Negative sentiment - unstake
            logger.info(f"Negative sentiment ({sentiment_score}), unstaking {stake_amount} TAO")
            result = await client.remove_stake(netuid, hotkey, stake_amount)
        else:
            # Neutral sentiment - no action
            logger.info("Neutral sentiment, no stake operation performed")
            return {
                "success": True,
                "operation": "none",
                "sentiment_score": 0,
                "message": "Neutral sentiment, no action taken"
            }
        
        # Save operation to database
        op_type = "stake" if sentiment_score > 0 else "unstake"
        stake_op = StakeOperation(
            netuid=netuid,
            hotkey=hotkey,
            operation_type=op_type,
            amount=stake_amount,
            sentiment_score=sentiment_score,
            successful=result.get("success", False),
            transaction_hash=result.get("transaction_hash"),
            error_message=result.get("error")
        )
        await engine.save(stake_op)
        
        return {
            "success": True,
            "sentiment_score": sentiment_score,
            "operation": op_type,
            "amount": stake_amount,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis and stake task: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }