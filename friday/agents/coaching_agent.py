from datetime import date
from pathlib import Path
from openai import OpenAI
from friday.config import get_settings
from friday.db.pool import get_pool

settings = get_settings()

client = OpenAI(
    base_url=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
)

PROMPT = (
    Path(__file__).parent
    / "prompts"
    / "coaching_prompt.txt"
).read_text(encoding="utf-8")


class CoachingAgent:

    async def get_today_coaching_data(self) -> dict:
        pool = get_pool()
        async with pool.acquire() as conn:
            # 1. Fetch Goals
            goals = await conn.fetch("SELECT * FROM current_goals")
            goals_dict = {row["goal_name"]: float(row["target_value"]) for row in goals}

            # 2. Fetch Food totals & items
            food_totals = await conn.fetchrow(
                """
                SELECT 
                    COALESCE(SUM(fi.calories), 0) AS calories,
                    COALESCE(SUM(fi.protein_g), 0) AS protein,
                    COALESCE(SUM(fi.carbs_g), 0) AS carbs,
                    COALESCE(SUM(fi.fat_g), 0) AS fat,
                    COALESCE(SUM(fi.fiber_g), 0) AS fiber
                FROM meals m
                JOIN food_items fi ON m.id = fi.meal_id
                WHERE m.meal_date = CURRENT_DATE AND m.status = 'logged'
                """
            )
            food_items = await conn.fetch(
                """
                SELECT fi.food_name, fi.quantity_desc
                FROM meals m
                JOIN food_items fi ON m.id = fi.meal_id
                WHERE m.meal_date = CURRENT_DATE AND m.status = 'logged'
                """
            )
            
            # 3. Fetch Steps
            steps = await conn.fetchval(
                "SELECT steps FROM daily_metrics WHERE metric_date = CURRENT_DATE"
            ) or 0

            # 4. Fetch Workouts
            workout = await conn.fetchrow(
                "SELECT id, is_rest_day, notes FROM workouts WHERE workout_date = CURRENT_DATE"
            )
            muscle_groups = []
            if workout and not workout["is_rest_day"]:
                mg_rows = await conn.fetch(
                    """
                    SELECT mg.name 
                    FROM workout_muscle_groups wmg
                    JOIN muscle_groups mg ON wmg.muscle_group_id = mg.id
                    WHERE wmg.workout_id = $1
                    """,
                    workout["id"]
                )
                muscle_groups = [r["name"] for r in mg_rows]

            return {
                "goals": goals_dict,
                "nutrition": dict(food_totals) if food_totals else {},
                "foods": [dict(f) for f in food_items],
                "steps": steps,
                "workout": {
                    "is_rest_day": workout["is_rest_day"] if workout else True,
                    "muscle_groups": muscle_groups,
                    "notes": workout["notes"] if workout else None
                } if workout else None
            }

    async def generate_daily_tip(self) -> str:
        data = await self.get_today_coaching_data()
        
        user_content = f"""Today's Stats (Date: {date.today()}):
Goals: {data['goals']}
Nutrition Intake: {data['nutrition']}
Foods Eaten: {data['foods']}
Steps Walked: {data['steps']}
Workout Details: {data['workout']}
"""

        response = client.responses.create(
            model=settings.azure_openai_deployment_main,
            input=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
        )
        return response.output_text.strip()