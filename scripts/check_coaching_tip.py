import asyncio
from friday.db.pool import close_pool, init_pool
from friday.agents.coaching_agent import CoachingAgent

async def main() -> None:
    await init_pool()
    try:
        agent = CoachingAgent()
        print("Today's database stats collected:")
        data = await agent.get_today_coaching_data()
        print(data)
        print("\n" + "=" * 50)
        print("Generated Daily Coaching Tip:")
        print("=" * 50)
        tip = await agent.generate_daily_tip()
        print(tip)
        
        print("\n" + "=" * 50)
        print("Generated Weekly Coaching Tip:")
        print("=" * 50)
        weekly_tip = await agent.generate_weekly_tip()
        print(weekly_tip)
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())