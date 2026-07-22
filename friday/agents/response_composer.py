from pathlib import Path
from typing import Any

from openai import OpenAI

from friday.config import get_settings
from friday.db.models import ConversationTurn

settings = get_settings()

client = OpenAI(
    base_url=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
)

PROMPT = (
    Path(__file__).parent
    / "prompts"
    / "composer_prompt.txt"
).read_text(encoding="utf-8")


class ResponseComposer:

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

    async def compose(
        self,
        *,
        message: str,
        raw_result: Any,
        context: list[ConversationTurn] | None = None,
    ) -> str:
        context = context or []
        history = self._format_context(context)

        user_prompt = f"""Conversation History:
{history}

Latest User Message:
{message}

Raw System / Tool Output:
{raw_result}
"""

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
                            "text": user_prompt,
                        }
                    ],
                },
            ],
            temperature=0.3,
        )

        return response.output_text.strip()
