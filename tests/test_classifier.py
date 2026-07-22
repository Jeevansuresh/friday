import asyncio

from friday.agents.classifier import Classifier


TESTS = [

    "I ate 3 eggs",

    "Today lunch chicken gravy",

    "Actually make it 4 eggs",

    "Protein today?",

    "Calories yesterday?",

    "Calories left?",

    "Push day done",

    "Today I trained chest and biceps",

    "Did I train legs?",

    "What muscle group did I miss?",

    "What's my protein goal?",

    "What's my calorie target?",

    "Should I bulk?",

    "How do I gain muscle?",
]


async def main():

    classifier = Classifier()

    for query in TESTS:

        result = await classifier.classify(
            context=[],
            message=query,
        )

        print("=" * 60)
        print(query)
        print(result.model_dump())


asyncio.run(main())