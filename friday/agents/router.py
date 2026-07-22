from friday.agents.nutrient_estimator import NutrientEstimator
from friday.agents.sql_generator import SQLGenerator
from friday.db.models import (
    ClassifiedIntent,
    IntentType,
)
from friday.db.queries import execute_sql, save_meal


class Router:

    def __init__(self):
        self.nutrient_estimator = NutrientEstimator()
        self.sql_generator = SQLGenerator()

    async def route(
        self,
        *,
        message: str,
        intent: ClassifiedIntent,
    ):

        match intent.intent:

            case IntentType.FOOD_LOG:

                estimate = await self.nutrient_estimator.estimate(
                    intent.foods,
                    message=message,
                )


                if estimate.needs_clarification:
                    return estimate.clarification_question

                meal_id = await save_meal(estimate)

                print("\n====== MEAL ESTIMATE ======")
                print(estimate.model_dump())
                print(f"Logged meal_id: {meal_id}")
                print("===========================\n")

                food_summary = ", ".join(
                    f"{f.quantity} {f.unit} {f.name}" for f in estimate.foods
                )
                return (
                    f"Logged meal ({estimate.meal_type.value}): {food_summary} "
                    f"(~{estimate.total_calories:.0f} kcal, {estimate.total_protein_g:.1f}g protein)."
                )

            case (
                IntentType.FOOD_QUERY
                | IntentType.WORKOUT_QUERY
                | IntentType.GOAL_QUERY
            ):

                result = await self.sql_generator.generate(
                    message
                )

                if not result.success:
                    return result.error

                try:
                    return await execute_sql(
                        result.action.sql,
                        result.action.parameters,
                    )

                except Exception as e:

                    retry = await self.sql_generator.regenerate(
                        request=message,
                        previous_sql=result.action.sql,
                        postgres_error=str(e),
                    )

                    if not retry.success:
                        return retry.error

                    return await execute_sql(
                        retry.action.sql,
                        retry.action.parameters,
                    )

            case IntentType.WORKOUT_LOG:
                return "Workout logging not implemented yet."

            case IntentType.COACHING:
                return "Coaching not implemented yet."

            case IntentType.UNKNOWN:
                return (
                    "I'm not sure what you meant. "
                    "Could you rephrase that?"
                )

            case _:
                return (
                    "I couldn't determine what to do with that message."
                )