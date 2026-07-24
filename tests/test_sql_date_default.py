import asyncio
from friday.agents.sql_generator import SQLGenerator

async def main():
    generator = SQLGenerator()
    queries = [
        "what are the total cals I ate",
        "breakdown my nutrition",
        "how many steps did I walk",
        "show my macros",
        "what did I eat yesterday" # should NOT default to CURRENT_DATE, should use yesterday
    ]
    
    for q in queries:
        print("\n" + "=" * 80)
        print("User query:", q)
        print("=" * 80)
        
        result = await generator.generate(q)
        if result.success and result.action:
            print("Reasoning:", result.action.reasoning)
            print("SQL:", result.action.sql)
            print("Parameters:", result.action.parameters)
        else:
            print("Generation failed:", result.error)

if __name__ == "__main__":
    asyncio.run(main())
