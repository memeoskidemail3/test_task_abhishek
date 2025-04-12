import os
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger

from app.worker import celery_app
from app.sentiment.datura import search_twitter
from app.sentiment.chutes import analyze_sentiment
from app.db.models import  SentimentAnalysis, StakeOperation, init_db
from app.blockchain.subtensor import perform_sentiment_based_staking

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
    print(f"Starting sentiment analysis and stake task for netuid={netuid}, hotkey={hotkey}")
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
        await init_db()
        from app.db.models import  get_engine
        engine = await get_engine()

        tweets = await search_twitter(netuid=netuid)

        print(f"Found {len(tweets)} tweets for subnet {netuid}")
        
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

        logger.info(f"Sentiment score for netuid {netuid}: {sentiment_score}")
        
        # Calculate stake amount (0.01 tao * sentiment score)
        stake_amount = abs(sentiment_score) * 0.01
        
        # Initialize blockchain client
        # result = await stake_based_on_sentiment(netuid, hotkey, sentiment_score)
        result = await perform_sentiment_based_staking(sentiment_score)
        
        logger.info(f"Stake operation result: {result}")

        # Perform stake/unstake operation based on sentiment
        
        
        # Save operation to database
        op_type = "stake" if sentiment_score > 0 else "unstake"
        stake_op = StakeOperation(
            netuid=netuid,
            hotkey=hotkey,
            operation_type=op_type,
            amount=stake_amount,
            sentiment_score=sentiment_score,
            successful=result[0],
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