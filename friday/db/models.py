"""
Pydantic models mirroring the DB schema.

Deliberately starts small — add a model here exactly when the phase that
needs it starts (see project README). Don't pre-build models for tables
you haven't wired up yet; you'll just end up reshaping them later.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Phase 2: Context Loader
# ------------------------------------------------------------------

class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ConversationTurn(BaseModel):
    role: Role
    content: str
    intent: str | None = None
    created_at: datetime | None = None


# ------------------------------------------------------------------
# Phase 3: Classifier
# ------------------------------------------------------------------

class IntentType(str, Enum):
    FOOD_LOG = "food_log"
    FOOD_QUERY = "food_query"
    FOOD_DELETE_LIST = "food_delete_list"
    FOOD_DELETE_EXECUTE = "food_delete_execute"
    WORKOUT_LOG = "workout_log"
    WORKOUT_QUERY = "workout_query"
    STEP_LOG = "step_log"
    GOAL_QUERY = "goal_query"
    COACHING = "coaching"
    UNKNOWN = "unknown"


class FoodMention(BaseModel):
    """
    Structured food extracted from the user's message.
    """

    name: str
    quantity: float | None = None
    unit: str | None = None


class ClassifiedIntent(BaseModel):
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None
    foods: list[FoodMention] = Field(default_factory=list)
    target_food_id: int | None = None
    workout_muscle_groups: list[str] = Field(default_factory=list)
    is_rest_day: bool = False
    steps: int | None = None


# ------------------------------------------------------------------
# Phase 4: Nutrient Estimation
# ------------------------------------------------------------------

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"



class FoodEstimate(BaseModel):
    """
    Nutrition estimate for one food item.
    """

    name: str

    quantity: float | None = None
    unit: str | None = None

    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None

    confidence: Confidence


# ------------------------------------------------------------------
# Database Models
# ------------------------------------------------------------------

class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MealStatus(str, Enum):
    LOGGED = "logged"
    SKIPPED = "skipped"


class MealEstimate(BaseModel):
    """
    Output from the Nutrient Estimator.
    """

    meal_type: MealType = MealType.SNACK

    foods: list[FoodEstimate]

    total_calories: float | None = None
    total_protein_g: float | None = None
    total_carbs_g: float | None = None
    total_fat_g: float | None = None
    total_fiber_g: float | None = None

    confidence: Confidence

    needs_clarification: bool = False
    clarification_question: str | None = None



class Meal(BaseModel):
    meal_date: date
    meal_type: MealType
    status: MealStatus = MealStatus.LOGGED


# ------------------------------------------------------------------
# Clarification state
# ------------------------------------------------------------------

class PendingClarification(BaseModel):
    """
    Saved state from a turn where the nutrient estimator asked for
    clarification. Held in memory on FridayClient between turns.
    """
    original_message: str               # the user's full original meal message
    foods: list[FoodMention]            # classifier's original food extractions
    clarification_question: str         # what the bot asked