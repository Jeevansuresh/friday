import asyncio

import discord

from friday.client import FridayClient
from friday.config import get_settings
from friday.db.pool import close_pool, init_pool


async def main():

    settings = get_settings()

    await init_pool()

    intents = discord.Intents.default()
    intents.message_content = True

    client = FridayClient(
        intents=intents,
        channel_id=settings.discord_channel_id,
    )

    try:
        await client.start(settings.discord_token)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())