"""
Central config. Every other module pulls settings from here instead of
reading os.environ directly, so there's exactly one place that knows
about .env.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # --------------------------------------------------
    # Discord
    # --------------------------------------------------

    discord_token: str
    discord_channel_id: int

    # --------------------------------------------------
    # Database
    # --------------------------------------------------

    database_url: str

    # --------------------------------------------------
    # Azure AI Foundry
    # Endpoint example:
    # https://<resource>.services.ai.azure.com/openai/v1
    # --------------------------------------------------

    azure_openai_endpoint: str
    azure_openai_api_key: str

    azure_openai_deployment_classifier: str
    azure_openai_deployment_main: str

    # --------------------------------------------------
    # Scheduler
    # --------------------------------------------------

    timezone: str = "Asia/Kolkata"
    notification_hours: str = "9,14,21"

    # --------------------------------------------------
    # Domain Constants
    # --------------------------------------------------

    muscle_groups: tuple[str, ...] = (
        "Chest",
        "Back",
        "Shoulders",
        "Biceps",
        "Triceps",
        "Legs",
    )

    context_window_turns: int = 10

    @property
    def notification_hour_list(self) -> list[int]:
        return [
            int(hour.strip())
            for hour in self.notification_hours.split(",")
        ]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()