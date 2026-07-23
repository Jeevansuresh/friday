from friday.agents.nutrient_estimator import NutrientEstimator
from friday.agents.sql_generator import SQLGenerator
from friday.db.models import (
    ClassifiedIntent,
    IntentType,
    PendingClarification,
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
                    return estimate.clarification_question, PendingClarification(
                        original_message=message,
                        foods=intent.foods,
                        clarification_question=estimate.clarification_question,
                    )

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
                ), None

            case (
                IntentType.FOOD_QUERY
                | IntentType.WORKOUT_QUERY
                | IntentType.GOAL_QUERY
            ):

                result = await self.sql_generator.generate(
                    message
                )

                if not result.success:
                    return result.error, None

                try:
                    return await execute_sql(
                        result.action.sql,
                        result.action.parameters,
                    ), None

                except Exception as e:

                    retry = await self.sql_generator.regenerate(
                        request=message,
                        previous_sql=result.action.sql,
                        postgres_error=str(e),
                    )

                    if not retry.success:
                        return retry.error, None

                    return await execute_sql(
                        retry.action.sql,
                        retry.action.parameters,
                    ), None

            case IntentType.WORKOUT_LOG:
                return "Workout logging not implemented yet.", None

            case IntentType.COACHING:
                return "Coaching not implemented yet.", None

            case IntentType.UNKNOWN:
                return (
                    "I'm not sure what you meant. "
                    "Could you rephrase that?"
                ), None

            case _:
                return (
                    "I couldn't determine what to do with that message."
                ), None

    async def route_clarification(
        self,
        *,
        answer: str,
        pending: PendingClarification,
    ) -> tuple[str, PendingClarification | None]:
        """
        Called when the user replies to a clarification question.
        Merges the answer into the original message and re-runs estimation
        using the original food list — bypasses the classifier entirely.
        """
        # Splice the answer into the original message so the estimator
        # has full context (meal type keywords, all food names, the answer).
        merged_message = (
            f"{pending.original_message} "
            f"[clarification: {pending.clarification_question} Answer: {answer}]"
        )

        print("\n====== CLARIFICATION MERGE ======")
        print(f"Original: {pending.original_message}")
        print(f"Answer:   {answer}")
        print(f"Merged:   {merged_message}")
        print("================================\n")

        estimate = await self.nutrient_estimator.estimate(
            pending.foods,
            message=merged_message,
        )

        # If still needs clarification (e.g. answer was ambiguous), persist again
        if estimate.needs_clarification:
            return estimate.clarification_question, PendingClarification(
                original_message=pending.original_message,
                foods=pending.foods,
                clarification_question=estimate.clarification_question,
            )

        meal_id = await save_meal(estimate)

        print("\n====== MEAL ESTIMATE (post-clarification) ======")
        print(estimate.model_dump())
        print(f"Logged meal_id: {meal_id}")
        print("================================================\n")

        food_summary = ", ".join(
            f"{f.quantity} {f.unit} {f.name}" for f in estimate.foods
        )
        return (
            f"Logged meal ({estimate.meal_type.value}): {food_summary} "
            f"(~{estimate.total_calories:.0f} kcal, {estimate.total_protein_g:.1f}g protein)."
        ), None