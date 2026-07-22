from friday.config import get_settings
from friday.db.models import ConversationTurn, Role
from friday.db.queries import (
    get_recent_messages,
    save_message,
)


class ContextLoader:

    async def add_user_message(
        self,
        content: str,
    ) -> None:
        await save_message(
            role=Role.USER,
            content=content,
        )

    async def add_assistant_message(
        self,
        content: str,
    ) -> None:
        await save_message(
            role=Role.ASSISTANT,
            content=content,
        )

    async def get_context(
        self,
    ) -> list[ConversationTurn]:
        settings = get_settings()

        return await get_recent_messages(
            settings.context_window_turns
        )