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
        print("Generated Coaching Tip:")
        print("=" * 50)
        tip = await agent.generate_daily_tip()
        print(tip)
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())