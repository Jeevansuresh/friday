import asyncio
from friday.db.pool import close_pool, init_pool

async def main():
    pool = await init_pool()
    try:
        async with pool.acquire() as conn:
            meals = await conn.fetch("SELECT * FROM meals ORDER BY id DESC LIMIT 10")
            print("=== Last 10 Meals ===")
            for m in meals:
                print(f"Meal ID: {m['id']} | Date: {m['meal_date']} | Type: {m['meal_type']} | Status: {m['status']} | Created: {m['created_at']}")
                foods = await conn.fetch("SELECT * FROM food_items WHERE meal_id = $1", m['id'])
                for f in foods:
                    print(f"  - Food ID: {f['id']} | Name: {f['food_name']} | Qty: {f['quantity_desc']} | Grams: {f['quantity_grams']} | Cal: {f['calories']} | P: {f['protein_g']} | C: {f['carbs_g']} | F: {f['fat_g']}")
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
