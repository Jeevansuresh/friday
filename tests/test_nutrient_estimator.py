"""
Phase 4 Test: Nutrient Estimator & Meal Persistence.

Tests both:
1. High-confidence food logging end-to-end (Classifier -> NutrientEstimator -> DB insert).
2. Low-confidence food logging (missing quantity -> returns clarification question, no DB write).

Usage:
    .\\venv\\Scripts\\python.exe -m tests.test_nutrient_estimator
"""

import asyncio

from friday.agents.classifier import Classifier
from friday.agents.router import Router
from friday.db.pool import close_pool, init_pool, get_pool


async def main():
    pool = await init_pool()

    classifier = Classifier()
    router = Router()

    try:
        # --------------------------------------------------
        # TEST 1: High Confidence Path ("3 eggs and 200g rice")
        # --------------------------------------------------
        print("\n" + "=" * 60)
        print("TEST 1: High Confidence Logging ('3 eggs and 200g rice')")
        print("=" * 60)

        msg1 = "today I ate 3 eggs and 200g rice"
        intent1 = await classifier.classify(context=[], message=msg1)
        print("Classified Intent:", intent1.intent.value, "| Foods extracted:", [f.model_dump() for f in intent1.foods])

        result1 = await router.route(message=msg1, intent=intent1)
        print("Router Result:", result1)

        # Verify DB contents
        async with pool.acquire() as conn:
            meal_rows = await conn.fetch("SELECT * FROM meals ORDER BY id DESC LIMIT 1")
            if meal_rows:
                meal_id = meal_rows[0]["id"]
                print(f"\n[DB Check] Latest Meal ID: {meal_id}, Date: {meal_rows[0]['meal_date']}, Type: {meal_rows[0]['meal_type']}")
                food_rows = await conn.fetch("SELECT food_name, quantity_desc, calories, protein_g, carbs_g, fat_g FROM food_items WHERE meal_id = $1", meal_id)
                for f in food_rows:
                    print(f"  - Food: {f['food_name']} | Qty: {f['quantity_desc']} | {f['calories']} kcal | P: {f['protein_g']}g | C: {f['carbs_g']}g | F: {f['fat_g']}g")
            else:
                print("\n❌ Error: No meal inserted into DB!")

        # --------------------------------------------------
        # TEST 2: Low Confidence / Clarification Path ("I ate chicken")
        # --------------------------------------------------
        print("\n" + "=" * 60)
        print("TEST 2: Low Confidence / Clarification Path ('I ate chicken')")
        print("=" * 60)

        msg2 = "I ate chicken"
        intent2 = await classifier.classify(context=[], message=msg2)
        print("Classified Intent:", intent2.intent.value, "| Foods extracted:", [f.model_dump() for f in intent2.foods])

        result2 = await router.route(message=msg2, intent=intent2)
        print("Router Result:", result2)

        # Verify no additional food items inserted
        async with pool.acquire() as conn:
            unresolved = await conn.fetchval("SELECT count(*) FROM food_items WHERE food_name = 'chicken' AND needs_clarification = TRUE")
            print(f"\n[DB Check] Unresolved chicken items in DB: {unresolved} (Should be 0)")

    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
