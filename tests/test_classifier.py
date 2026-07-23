import pytest
from friday.agents.classifier import Classifier
from friday.db.models import IntentType

@pytest.mark.anyio
async def test_classify_food_delete_list():
    classifier = Classifier()
    result = await classifier.classify(context=[], message="/fix")
    assert result.intent == IntentType.FOOD_DELETE_LIST

@pytest.mark.anyio
async def test_classify_food_delete_execute():
    classifier = Classifier()
    result = await classifier.classify(context=[], message="/delete 12")
    assert result.intent == IntentType.FOOD_DELETE_EXECUTE
    assert result.target_food_id == 12

@pytest.mark.anyio
async def test_classify_food_log():
    classifier = Classifier()
    result = await classifier.classify(context=[], message="I had 2 eggs")
    assert result.intent == IntentType.FOOD_LOG