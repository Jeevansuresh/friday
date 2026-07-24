import asyncio
from friday.agents.classifier import Classifier
from friday.agents.nutrient_estimator import NutrientEstimator
from friday.db.pool import close_pool, init_pool

async def main():
    await init_pool()
    try:
        classifier = Classifier()
        estimator = NutrientEstimator()
        
        msg = "467 g of rice in seeraga samba chicken biriyani and   350g of chicken breast (with some bone pieces)"
        print("User message:", msg)
        
        intent = await classifier.classify(context=[], message=msg)
        print("\n=== Classified Intent ===")
        print("Intent:", intent.intent.value)
        print("Foods extracted:", [f.model_dump() for f in intent.foods])
        
        result = await estimator.estimate(intent.foods, message=msg)
        print("\n=== Nutrient Estimate ===")
        print("Meal Type:", result.meal_type)
        print("Total Calories:", result.total_calories)
        print("Total Protein:", result.total_protein_g)
        print("Total Carbs:", result.total_carbs_g)
        print("Total Fat:", result.total_fat_g)
        
        print("\n=== Foods Details ===")
        for food in result.foods:
            print(f"Food: {food.name} | Qty: {food.quantity} {food.unit} | Calories: {food.calories} | Protein: {food.protein_g}g | Carbs: {food.carbs_g}g | Fat: {food.fat_g}g")
            
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
