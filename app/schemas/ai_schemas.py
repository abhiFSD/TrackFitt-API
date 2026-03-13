from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime
from app.models.models import AIOperationType, FitnessLevel, ActivityLevel # Import enums from models
from app.schemas.schemas import ExerciseBase # Correct the import for ExerciseBase

class AIOperationType(str, Enum):
    WORKOUT_CREATION = "workout_creation"
    DIET_RECOMMENDATION = "diet_recommendation"
    FITNESS_ADVICE = "fitness_advice"
    PROGRESS_ANALYSIS = "progress_analysis"

class AITrackingBase(BaseModel):
    user_prompt: str
    input_data: Optional[Dict[str, Any]] = None
    operation_type: AIOperationType

class AITrackingCreate(AITrackingBase):
    pass

class AITrackingResponse(AITrackingBase):
    id: int
    user_id: int
    response_data: Optional[Dict[str, Any]] = None
    status: str
    duration_ms: Optional[int] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

# Workout creation specific schemas
class ExerciseInfo(BaseModel):
    exercise_id: str
    name: str
    category: Optional[str] = None
    muscle_groups: Optional[str] = None
    equipment: Optional[str] = None

class WorkoutExerciseCreate(BaseModel):
    exercise_id: str
    sets: int
    reps: int
    weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None
    notes: Optional[str] = None

class WorkoutAIExercise(BaseModel):
    exercise_id: int # Changed from str based on latest findings
    sets: int
    reps: int
    weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None
    notes: Optional[str] = None

class WorkoutAIResponse(BaseModel):
    title: str
    description: str
    duration_minutes: int
    difficulty_level: str
    exercises: List[WorkoutAIExercise]
    ai_notes: Optional[str] = None

class WorkoutAIRequest(BaseModel):
    user_id: int # Keep track of who made the request
    user_prompt: str
    fitness_level: Optional[str] = None
    preferred_duration: Optional[int] = None # in minutes
    preferred_equipment: Optional[List[str]] = None
    target_muscle_groups: Optional[List[str]] = None
    available_exercises: Optional[List[ExerciseBase]] = None # Use the correctly imported ExerciseBase
    shared_profile_data: Optional[Dict[str, Any]] = None

# Schema for creating AITracking (used internally by service)
class AITrackingCreate(BaseModel):
    user_id: int
    operation_type: str # Use string representation of AIOperationType enum
    user_prompt: Optional[str] = None
    input_data: Optional[str] = None # Store as JSON string
    response_data: Optional[str] = None # Store as JSON string
    status: str = "completed"
    duration_ms: Optional[int] = None
    metadata: Optional[str] = None # Store as JSON string

# ---> ADD AI History Response Schema <---
class AITrackingResponse(BaseModel):
    id: int
    user_id: int
    operation_type: AIOperationType
    created_at: datetime
    user_prompt: Optional[str] = None
    input_data: Optional[str] = None # Return JSON strings for now
    response_data: Optional[str] = None # Return JSON strings for now
    status: str
    duration_ms: Optional[int] = None
    extra_data: Optional[str] = None

    class Config:
        orm_mode = True # Enable reading data directly from ORM models
        from_attributes = True # Use this instead of orm_mode for Pydantic v2+
# ---> END AI History Response Schema <--- 