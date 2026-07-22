from pathlib import Path

from openai import OpenAI

from friday.config import get_settings
from friday.validation.sql_schema import SQLGenerationResult

settings = get_settings()

client = OpenAI(
    base_url=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
)

PROMPT = (
    Path(__file__).parent
    / "prompts"
    / "sql_generator_prompt.txt"
).read_text()

SCHEMA = Path("schema.sql").read_text()

SYSTEM_PROMPT = f"""
{PROMPT}

-------------------------
DATABASE SCHEMA
-------------------------

{SCHEMA}
"""


class SQLGenerator:

    def _generate(
        self,
        user_prompt: str,
    ) -> SQLGenerationResult:
        response = client.responses.create(
            model=settings.azure_openai_deployment_main,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": SYSTEM_PROMPT,
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
            temperature=0,
        )

        return SQLGenerationResult.model_validate_json(
            response.output_text
        )

    async def generate(
        self,
        request: str,
    ) -> SQLGenerationResult:

        result = self._generate(request)

        print("\n====== SQL GENERATOR ======")
        print(result.model_dump_json(indent=2))
        print("===========================\n")

        return result

    async def regenerate(
        self,
        *,
        request: str,
        previous_sql: str,
        postgres_error: str,
    ) -> SQLGenerationResult:
        """
        Retry SQL generation after PostgreSQL rejects the previous query.
        """

        retry_prompt = f"""
Original request:
{request}

Previous SQL:
{previous_sql}

PostgreSQL error:
{postgres_error}

The previous SQL failed to execute.

Correct the SQL while preserving the original intent.

Return ONLY valid JSON matching the required schema.
"""

        result = self._generate(retry_prompt)

        print("\n====== SQL RETRY ======")
        print(result.model_dump_json(indent=2))
        print("=======================\n")

        return result