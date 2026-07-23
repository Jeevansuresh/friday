import traceback

import discord

from friday.agents.classifier import Classifier
from friday.agents.response_composer import ResponseComposer
from friday.agents.router import Router
from friday.context.loader import ContextLoader
from friday.db.models import PendingClarification


class FridayClient(discord.Client):

    def __init__(
        self,
        *,
        channel_id: int,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.channel_id = channel_id

        self.context_loader = ContextLoader()
        self.classifier = Classifier()
        self.router = Router()
        self.composer = ResponseComposer()

        # Holds state when the nutrient estimator needs a clarification answer
        self.pending_clarification: PendingClarification | None = None

    async def on_ready(self):
        print(f"Logged in as {self.user} ({self.user.id})")

    async def on_message(self, message: discord.Message):
        try:

            if message.author.bot:
                return

            if message.channel.id != self.channel_id:
                return

            print(
                f"\n[{message.channel.name}] "
                f"{message.author.display_name}: {message.content}"
            )

            # --------------------------------------------------
            # STEP 1: Save user message
            # --------------------------------------------------

            await self.context_loader.add_user_message(
                message.content
            )

            # --------------------------------------------------
            # STEP 2: Load context
            # --------------------------------------------------

            history = await self.context_loader.get_context()

            print("\n====== CONTEXT ======")

            for turn in history:
                print(
                    f"{turn.role.value.upper()}: {turn.content}"
                )

            print("=====================")

            # --------------------------------------------------
            # STEP 3 & 4: Classify + Route
            # If a clarification answer is pending, bypass the
            # classifier and feed the answer directly to the router.
            # --------------------------------------------------

            if self.pending_clarification is not None:
                print("\n====== CLARIFICATION TURN ======")
                print(f"Pending: {self.pending_clarification.clarification_question}")
                print("================================")

                result, new_pending = await self.router.route_clarification(
                    answer=message.content,
                    pending=self.pending_clarification,
                )
                self.pending_clarification = new_pending

            else:
                intent = await self.classifier.classify(
                    context=history,
                    message=message.content,
                )

                print("\n====== CLASSIFIER ======")
                print(intent.model_dump())
                print("========================")

                result, new_pending = await self.router.route(
                    message=message.content,
                    intent=intent,
                )
                self.pending_clarification = new_pending

            print("\n======== ROUTER ========")
            print(result)
            print("========================\n")

            # --------------------------------------------------
            # STEP 5: Compose Response
            # --------------------------------------------------

            final_reply = await self.composer.compose(
                message=message.content,
                raw_result=result,
                context=history,
            )

            print("\n====== COMPOSER ======")
            print(final_reply)
            print("======================\n")

            # --------------------------------------------------
            # STEP 6: Send Reply
            # --------------------------------------------------

            await message.channel.send(final_reply)

            # --------------------------------------------------
            # STEP 7: Save assistant reply
            # --------------------------------------------------

            await self.context_loader.add_assistant_message(
                final_reply
            )


        except Exception:
            print("\n===== ERROR IN on_message() =====")
            traceback.print_exc()
            print("=================================\n")