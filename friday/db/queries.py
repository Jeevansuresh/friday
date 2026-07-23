from datetime import date
from typing import Any

from friday.db.models import Confidence, ConversationTurn, MealEstimate, Role
from friday.db.pool import get_pool



async def save_message(
    *,
    role: Role,
    content: str,
    intent: str | None = None,
) -> None:
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversation_context (
                role,
                content,
                intent
            )
            VALUES ($1, $2, $3)
            """,
            role.value,
            content,
            intent,
        )


async def get_recent_messages(
    limit: int = 10,
) -> list[ConversationTurn]:
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                role,
                content,
                intent,
                created_at
            FROM conversation_context
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )

    rows.reverse()

    return [
        ConversationTurn(
            role=Role(row["role"]),
            content=row["content"],
            intent=row["intent"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def execute_sql(
    sql: str,
    parameters: list[Any] | None = None,
) -> Any:
    """
    Execute a parameterized SQL statement.

    Returns:
        SELECT -> list[asyncpg.Record]
        INSERT/UPDATE/DELETE -> status string
    """

    parameters = parameters or []

    pool = get_pool()

    async with pool.acquire() as conn:

        command = sql.strip().split(maxsplit=1)[0].upper()

        if command == "SELECT":
            return await conn.fetch(sql, *parameters)

        return await conn.execute(sql, *parameters)


async def save_meal(
    estimate: MealEstimate,
    meal_date: date | None = None,
) -> int:
    """
    Saves a MealEstimate to the `meals` and `food_items` tables.
    Defaults meal_date to today's date if not provided.
    Returns the ID of the meal.
    """
    if meal_date is None:
        meal_date = date.today()

    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            meal_id = await conn.fetchval(
                """
                SELECT id FROM meals
                WHERE meal_date = $1 AND meal_type = $2 AND status = 'logged'
                """,
                meal_date,
                estimate.meal_type.value,
            )

            if meal_id is None:
                meal_id = await conn.fetchval(
                    """
                    INSERT INTO meals (meal_date, meal_type, status)
                    VALUES ($1, $2, 'logged')
                    RETURNING id
                    """,
                    meal_date,
                    estimate.meal_type.value,
                )

            for food in estimate.foods:
                confidence_val = (
                    "high" if food.confidence == Confidence.HIGH else "low"
                )
                quantity_desc = f"{food.quantity} {food.unit}".strip()

                await conn.execute(
                    """
                    INSERT INTO food_items (
                        meal_id,
                        food_name,
                        quantity_desc,
                        confidence,
                        needs_clarification,
                        calories,
                        protein_g,
                        carbs_g,
                        fat_g,
                        fiber_g
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    meal_id,
                    food.name,
                    quantity_desc,
                    confidence_val,
                    estimate.needs_clarification,
                    food.calories,
                    food.protein_g,
                    food.carbs_g,
                    food.fat_g,
                    food.fiber_g,
                )

            return meal_id


async def get_todays_food_items() -> list[dict]:
    """
    Returns a list of all food items logged today, including their DB IDs, names,
    quantities, and meal types, so they can be shown to the user.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT fi.id, m.meal_type, fi.food_name, fi.quantity_desc, fi.calories, fi.protein_g
            FROM food_items fi
            JOIN meals m ON m.id = fi.meal_id
            WHERE m.meal_date = CURRENT_DATE
            ORDER BY m.meal_type, fi.id
            """
        )
        return [dict(row) for row in rows]


async def delete_food_item(food_item_id: int) -> bool:
    """
    Deletes a specific food item by its ID.
    If the parent meal has no food items left, deletes the meal too.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            meal_id = await conn.fetchval(
                "SELECT meal_id FROM food_items WHERE id = $1",
                food_item_id
            )
            if not meal_id:
                return False

            await conn.execute("DELETE FROM food_items WHERE id = $1", food_item_id)

            remaining = await conn.fetchval(
                "SELECT COUNT(*) FROM food_items WHERE meal_id = $1",
                meal_id
            )
            if remaining == 0:
                await conn.execute("DELETE FROM meals WHERE id = $1", meal_id)

            return True