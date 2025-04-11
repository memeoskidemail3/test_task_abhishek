import asyncio
import bittensor
from bittensor import AsyncSubtensor

async def get_tao_dividends_per_subnet(netuid: int, hotkey: str):
    subtensor = AsyncSubtensor()
    substrate = subtensor.substrate
    try:
        result = await substrate.query(
            module='SubtensorModule',
            storage_function='TaoDividendsPerSubnet',
            params=[netuid, hotkey]
        )
        print(f"TaoDividendsPerSubnet(netuid={netuid}, hotkey={hotkey}) = {result.value}")
        return result.value
    except Exception as e:
        print(f"Error querying TaoDividendsPerSubnet: {e}")
        return None
