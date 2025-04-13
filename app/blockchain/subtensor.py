import os
import asyncio
from bittensor_wallet import Wallet
from app.utils.config import settings
from loguru import logger


# Load wallet config from settings
WALLET_NAME = settings.WALLET_NAME
WALLET_HOTKEY = settings.WALLET_HOTKEY
WALLET_PATH = os.path.expanduser("~/.bittensor/wallets")


async def get_tao_dividends_per_subnet(netuid: int, hotkey: str):
    try:
        # Import inside the function to avoid Celery multiprocessing issues
        from bittensor import AsyncSubtensor
        subtensor = AsyncSubtensor()
        substrate = subtensor.substrate

        result = await substrate.query(
            module='SubtensorModule',
            storage_function='TaoDividendsPerSubnet',
            params=[netuid, hotkey]
        )
        logger.info(f"TaoDividendsPerSubnet(netuid={netuid}, hotkey={hotkey}) = {result.value}")
        return result.value

    except Exception as e:
        logger.error(f"Error querying TaoDividendsPerSubnet: {e}")
        return None


async def stake_based_on_sentiment(netuid: int, hotkey: str, sentiment_score: float):
    """
    Stake or unstake TAO based on sentiment score.

    Args:
        netuid: Subnet ID.
        hotkey: Hotkey address to stake/unstake from.
        sentiment_score: Float value from -100 to 100. Positive stakes, negative unstakes.
    """
    try:
        # Import inside the function
        from bittensor import AsyncSubtensor
        
        subtensor = AsyncSubtensor()

        # Convert sentiment to TAO amount
        amount = 0.01 * sentiment_score
        amount_rao = int(abs(amount) * 10**9)

        import bittensor as bt
        logger.info(f"Using wallet path: {WALLET_PATH}")
        wallet = bt.wallet(name=WALLET_NAME, hotkey=WALLET_HOTKEY)
        
        logger.info(f"Using wallet: ")

        if sentiment_score < 0:
            logger.info(f"Unstaking {amount} TAO (~{amount_rao} RAO) for netuid={netuid}")
            result = await subtensor.unstake(
                netuid=netuid,
                wallet=wallet,
                amount=amount_rao
            )
        else:
            logger.info(f"Staking {amount} TAO (~{amount_rao} RAO) for netuid={netuid}")
            result = await subtensor.add_stake(
                netuid=netuid,
                wallet=wallet,
                amount=amount_rao
            )

        logger.success(f"Stake/Unstake transaction sent: {result}")
        return result

    except Exception as e:
        logger.error(f"Error during stake/unstake based on sentiment: {e}")
        return None
