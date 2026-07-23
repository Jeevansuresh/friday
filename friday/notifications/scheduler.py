from apscheduler.schedulers.asyncio import AsyncioScheduler
from apscheduler.triggers.cron import CronTrigger
import discord

from friday.config import get_settings
from friday.agents.coaching_agent import CoachingAgent

settings = get_settings()
coaching_agent = CoachingAgent()
scheduler = AsyncioScheduler(timezone=settings.timezone)

async def send_daily_tip(client: discord.Client):
    try:
        channel = client.get_channel(settings.discord_channel_id)
        if channel:
            tip = await coaching_agent.generate_daily_tip()
            await channel.send(tip)
    except Exception as e:
        print(f"Error executing daily tip notification: {e}")

async def send_weekly_tip(client: discord.Client):
    try:
        channel = client.get_channel(settings.discord_channel_id)
        if channel:
            tip = await coaching_agent.generate_weekly_tip()
            await channel.send(tip)
    except Exception as e:
        print(f"Error executing weekly tip notification: {e}")

def start_scheduler(client: discord.Client):
    # Daily coaching at 11 PM
    scheduler.add_job(
        send_daily_tip,
        trigger=CronTrigger(hour=23, minute=0),
        args=[client],
        id="daily_tip_job",
        replace_existing=True
    )
    # Weekly coaching review at 11 PM every Sunday
    scheduler.add_job(
        send_weekly_tip,
        trigger=CronTrigger(day_of_week="sun", hour=23, minute=0),
        args=[client],
        id="weekly_tip_job",
        replace_existing=True
    )
    scheduler.start()
    print("Coaching scheduler started for 11 PM daily (and Sunday weekly reviews).")