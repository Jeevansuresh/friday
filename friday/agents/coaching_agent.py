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

WEEKLY_PROMPT = (
    Path(__file__).parent
    / "prompts"
    / "weekly_coaching_prompt.txt"
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
                }
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

    async def get_weekly_coaching_data(self) -> dict:
        pool = get_pool()
        async with pool.acquire() as conn:
            # 1. Fetch Goals
            goals = await conn.fetch("SELECT * FROM current_goals")
            goals_dict = {row["goal_name"]: float(row["target_value"]) for row in goals}

            # 2. Daily nutrition totals for last 7 days
            nutrition_history = await conn.fetch(
                """
                SELECT 
                    m.meal_date,
                    COALESCE(SUM(fi.calories), 0) AS calories,
                    COALESCE(SUM(fi.protein_g), 0) AS protein
                FROM meals m
                LEFT JOIN food_items fi ON m.id = fi.meal_id
                WHERE m.meal_date >= CURRENT_DATE - INTERVAL '6 days' 
                  AND m.meal_date <= CURRENT_DATE
                  AND m.status = 'logged'
                GROUP BY m.meal_date
                ORDER BY m.meal_date
                """
            )

            # 3. Daily step counts for last 7 days
            steps_history = await conn.fetch(
                """
                SELECT metric_date, steps
                FROM daily_metrics
                WHERE metric_date >= CURRENT_DATE - INTERVAL '6 days'
                  AND metric_date <= CURRENT_DATE
                ORDER BY metric_date
                """
            )

            # 4. Workouts logged in the last 7 days
            workout_rows = await conn.fetch(
                """
                SELECT w.id, w.workout_date, w.is_rest_day
                FROM workouts w
                WHERE w.workout_date >= CURRENT_DATE - INTERVAL '6 days'
                  AND w.workout_date <= CURRENT_DATE
                ORDER BY w.workout_date
                """
            )
            
            workouts_history = []
            for row in workout_rows:
                muscle_groups = []
                if not row["is_rest_day"]:
                    mg_rows = await conn.fetch(
                        """
                        SELECT mg.name 
                        FROM workout_muscle_groups wmg
                        JOIN muscle_groups mg ON wmg.muscle_group_id = mg.id
                        WHERE wmg.workout_id = $1
                        """,
                        row["id"]
                    )
                    muscle_groups = [r["name"] for r in mg_rows]
                
                workouts_history.append({
                    "workout_date": str(row["workout_date"]),
                    "is_rest_day": row["is_rest_day"],
                    "muscle_groups": muscle_groups
                })

            return {
                "goals": goals_dict,
                "nutrition_history": [dict(r) for r in nutrition_history],
                "steps_history": [dict(r) for r in steps_history],
                "workouts_history": workouts_history
            }

    async def generate_weekly_tip(self) -> str:
        data = await self.get_weekly_coaching_data()
        
        user_content = f"""Weekly Stats (Last 7 Days, ending {date.today()}):
Goals: {data['goals']}
Daily Nutrition: {data['nutrition_history']}
Daily Steps: {data['steps_history']}
Logged Workouts: {data['workouts_history']}
"""

        response = client.responses.create(
            model=settings.azure_openai_deployment_main,
            input=[
                {"role": "system", "content": WEEKLY_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
        )
        return response.output_text.strip()