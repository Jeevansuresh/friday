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

@pytest.mark.anyio
async def test_classify_workout_log():
    classifier = Classifier()
    result = await classifier.classify(context=[], message="I worked out my chest, triceps and shoulders today")
    assert result.intent == IntentType.WORKOUT_LOG
    assert "Chest" in result.workout_muscle_groups
    assert "Triceps" in result.workout_muscle_groups
    assert "Shoulders" in result.workout_muscle_groups

@pytest.mark.anyio
async def test_classify_rest_day():
    classifier = Classifier()
    result = await classifier.classify(context=[], message="today is rest day")
    assert result.intent == IntentType.WORKOUT_LOG
    assert result.is_rest_day is True

@pytest.mark.anyio
async def test_classify_step_log():
    classifier = Classifier()
    result = await classifier.classify(context=[], message="also I did 6994 steps today")
    assert result.intent == IntentType.STEP_LOG
    assert result.steps == 6994