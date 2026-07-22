from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

from openai import OpenAI

from friday.config import get_settings
from friday.db.models import (
    FoodMention,
    MealEstimate,
)

settings = get_settings()

client = OpenAI(
    base_url=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
)

PROMPT = (
    Path(__file__).parent
    / "prompts"
    / "nutrient_prompt.txt"
).read_text()


class NutrientEstimator:

    async def estimate(
        self,
        foods: list[FoodMention],
        message: str = "",
    ) -> MealEstimate:

        payload = json.dumps(
            [food.model_dump() for food in foods],
            indent=2,
        )

        ist = timezone(timedelta(hours=5, minutes=30))
        ist_time = datetime.now(ist).strftime("%H:%M")

        user_content = (
            f"User message: \"{message}\"\n"
            f"Current IST time: {ist_time}\n\n"
            f"Foods:\n{payload}"
        )

        response = client.responses.create(
            model=settings.azure_openai_deployment_main,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": PROMPT,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": user_content,
                        }
                    ],
                },
            ],
            temperature=0,
        )

        print("\n====== NUTRIENT RAW OUTPUT ======")
        print(response.output_text)
        print("================================\n")

        return MealEstimate.model_validate_json(
            response.output_text
        )