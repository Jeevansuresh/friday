import asyncio

from friday.agents.sql_generator import SQLGenerator

generator = SQLGenerator()

QUERIES = [

    # ---------- READ ----------

    "What did I eat today?",
    "How much protein did I eat today?",
    "How many calories do I have left today?",
    "Did I hit my protein goal today?",
    "When did I last train chest?",
    "How many times have I trained legs this month?",
    "What was my last message?",

    # ---------- WRITE ----------

    "Log that I ate 2 bananas for breakfast.",
    "Add 100g chicken to today's lunch.",
    "Update today's breakfast to 4 eggs instead of 3.",
    "Delete today's snack.",
    "Mark today's dinner as skipped.",
    "Log that today was a rest day.",
    "Set my protein goal to 160g.",

    # ---------- INVALID ----------

    "Tell me a joke.",
]


async def main():

    for i, query in enumerate(QUERIES, start=1):

        print("\n" + "=" * 100)
        print(f"[{i}] {query}")
        print("=" * 100)

        try:
            result = await generator.generate(query)

            print("SUCCESS :", result.success)

            if result.action:
                print("\nReasoning")
                print(result.action.reasoning)

                print("\nSQL")
                print(result.action.sql)

                print("\nParameters")
                print(result.action.parameters)

            if result.error:
                print("\nError")
                print(result.error)

        except Exception as e:
            print(e)


asyncio.run(main())