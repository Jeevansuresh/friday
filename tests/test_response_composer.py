"""
Phase 6 Test: Full Pipeline with Response Composer.

Tests full flow: User Message -> Classifier -> Router -> Tool Agent -> ResponseComposer -> Natural Reply

Usage:
    .\\venv\\Scripts\\python.exe -m tests.test_response_composer
"""

import asyncio
import sys

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


from friday.agents.classifier import Classifier
from friday.agents.response_composer import ResponseComposer
from friday.agents.router import Router
from friday.db.pool import close_pool, init_pool


TEST_MESSAGES = [
    "What did I eat today?",
    "How much protein did I eat today?",
    "today I ate 2 eggs and 150g oats for breakfast",
    "What is my protein goal?",
]


async def main():
    pool = await init_pool()

    classifier = Classifier()
    router = Router()
    composer = ResponseComposer()

    try:
        for msg in TEST_MESSAGES:
            print("\n" + "=" * 70)
            print(f"USER: {msg}")
            print("=" * 70)

            intent = await classifier.classify(context=[], message=msg)
            raw_result = await router.route(message=msg, intent=intent)

            final_reply = await composer.compose(
                message=msg,
                raw_result=raw_result,
                context=[],
            )

            print("\n[FRIDAY REPLY]:")
            print(final_reply)


    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
