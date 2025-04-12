import os
from bittensor_wallet import Wallet
from app.utils.config import settings
from loguru import logger
import asyncio
import subprocess
import os
import threading
from decimal import Decimal


WALLET_NAME = settings.WALLET_NAME
WALLET_HOTKEY = settings.WALLET_HOTKEY
WALLET_PATH = os.path.expanduser("~/.bittensor/wallets")


async def get_tao_dividends_per_subnet(netuid: int, hotkey: str):
    try:
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

def input_password(password, process):
    """Function to input password to subprocess when prompted"""
    try:
        process.stdin.write(password + "\n")
        process.stdin.flush()
    except Exception as e:
        logger.error(f"Error inputting password: {e}")

async def perform_sentiment_based_staking(sentiment_score, wallet_password="Test@123#"):
    """
    Perform staking based on sentiment analysis with automated password entry.
    
    Args:
        sentiment_score: Int between -100 and 100
        wallet_name: Name of the wallet
        wallet_password: Password for the wallet
    """
    try:
        import bittensor as bt
        # Calculate stake amount based on sentiment
        amount = abs(sentiment_score) * Decimal('0.01')
        
        # Default parameters
        netuid = 18
        hotkey_ss58 = "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v"
        
        # Create a command to run in a subprocess
        if sentiment_score > 0:
            cmd = f"btcli stake add --wallet.name {WALLET_NAME} --wallet.hotkey default --amount {amount} --netuid {netuid} --hotkey {hotkey_ss58}"
        else:
            cmd = f"btcli stake remove --wallet.name {WALLET_NAME} --wallet.hotkey default --amount {amount} --netuid {netuid} --hotkey {hotkey_ss58}"
        
        # Execute the command as a subprocess with password input
        process = subprocess.Popen(
            cmd.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Start a thread to input the password when prompted
        input_thread = threading.Thread(target=input_password, args=(wallet_password, process))
        input_thread.start()
        
        # Get the output
        stdout, stderr = process.communicate(timeout=60)
        
        if process.returncode != 0:
            logger.error(f"Error: {stderr}")
            return False, stderr
        else:
            logger.info(f"Success: {stdout}")
            return True, stdout
        
    except Exception as e:
        logger.error(f"Error in sentiment-based staking: {e}")
        return False, str(e)
