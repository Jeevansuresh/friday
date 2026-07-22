from pathlib import Path

from openai import OpenAI

from friday.config import get_settings
from friday.db.models import ClassifiedIntent, ConversationTurn

settings = get_settings()

client = OpenAI(
    base_url=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
)

PROMPT = (
    Path(__file__).parent
    / "prompts"
    / "classifier_prompt.txt"
).read_text(encoding="utf-8")


class Classifier:

    def _format_context(
        self,
        context: list[ConversationTurn],
    ) -> str:

        if not context:
            return "No previous conversation."

        return "\n".join(
            f"{turn.role.value.upper()}: {turn.content}"
            for turn in context
        )

    async def classify(
        self,
        *,
        context: list[ConversationTurn],
        message: str,
    ) -> ClassifiedIntent:

        history = self._format_context(context)

        user_prompt = f"""Conversation History

{history}

Latest User Message

{message}
"""

        response = client.responses.create(
            model=settings.azure_openai_deployment_classifier,
            input=[
                {
                    "role": "system",
                    "content": PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
        )

        return ClassifiedIntent.model_validate_json(
            response.output_text
        )