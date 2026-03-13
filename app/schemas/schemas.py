from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import List, Optional, Any
from datetime import datetime, date
from enum import Enum

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class TokenRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TokenTransactionType(str, Enum):
    EARN = "earn"
    SPEND = "spend"
    ADMIN_ADJUSTMENT = "admin_adjustment"

# User schemas
class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str
    email: EmailStr
    role: Optional[UserRole] = UserRole.USER

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

# UserProfile schemas
class FitnessLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"

class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"

class UserProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # Basic Information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    profile_image_url: Optional[str] = None
    
    # Physical Metrics
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    
    # Fitness Data
    fitness_level: Optional[FitnessLevel] = FitnessLevel.BEGINNER
    activity_level: Optional[ActivityLevel] = ActivityLevel.MODERATELY_ACTIVE
    
    # Goals
    weight_goal_kg: Optional[float] = None
    weekly_workout_goal: Optional[int] = 3
    
    # Preferences
    preferred_workout_duration: Optional[int] = 45
    preferred_workout_days: Optional[list[str]] = []
    favorite_muscle_groups: Optional[list[str]] = []
    
    # Health Data
    has_injuries: Optional[bool] = False
    injury_notes: Optional[str] = None
    has_medical_conditions: Optional[bool] = False
    medical_notes: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

# User with profile
class UserWithProfile(User):
    profile: Optional[UserProfile] = None

# ExerciseCategory schemas
class ExerciseCategoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    description: Optional[str] = None

class ExerciseCategoryCreate(ExerciseCategoryBase):
    pass

class ExerciseCategory(ExerciseCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

# Exercise schemas
class ExerciseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    exercise_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    muscle_groups: Optional[str] = None
    difficulty: Optional[str] = None
    equipment: Optional[str] = None
    instructions: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    form_tips: Optional[str] = None
    common_mistakes: Optional[str] = None
    variations: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ExerciseCreate(ExerciseBase):
    pass

class Exercise(ExerciseBase):
    id: int
    category_relation: Optional[ExerciseCategory] = None

# WorkoutExerciseSet schemas
class WorkoutExerciseSetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    set_number: int
    reps: int
    weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None

class WorkoutExerciseSetCreate(WorkoutExerciseSetBase):
    pass

class WorkoutExerciseSet(WorkoutExerciseSetBase):
    id: int
    workout_exercise_id: int

# WorkoutExercise schemas
class WorkoutExerciseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    exercise_id: int
    sets: int
    reps: int
    weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None
    notes: Optional[str] = None

class WorkoutExerciseCreate(WorkoutExerciseBase):
    set_details: Optional[List[WorkoutExerciseSetCreate]] = None

class WorkoutExercise(WorkoutExerciseBase):
    id: int
    workout_id: int
    exercise: Exercise
    set_details: Optional[List[WorkoutExerciseSet]] = []

# Workout schemas
class WorkoutBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str
    description: Optional[str] = None
    duration_minutes: int
    is_template: Optional[bool] = False
    is_published: Optional[bool] = False

class WorkoutCreate(WorkoutBase):
    exercises: List[WorkoutExerciseCreate]

class Workout(WorkoutBase):
    id: int
    date: datetime
    user_id: int
    exercises: List[WorkoutExercise]

# WorkoutHistoryExerciseSet schemas
class WorkoutHistoryExerciseSetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    set_number: int
    planned_reps: int
    planned_weight: Optional[float] = None
    actual_reps: Optional[int] = None
    actual_weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None
    completion_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None

class WorkoutHistoryExerciseSetCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    set_number: int
    planned_reps: int
    planned_weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None

class WorkoutHistoryExerciseSet(WorkoutHistoryExerciseSetBase):
    id: int
    workout_history_exercise_id: int

# WorkoutHistoryExercise schemas
class WorkoutHistoryExerciseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    exercise_id: int
    sets: int
    reps: int
    weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None
    notes: Optional[str] = None

class WorkoutHistoryExerciseCreate(WorkoutHistoryExerciseBase):
    set_details: Optional[List[WorkoutHistoryExerciseSetCreate]] = None

class WorkoutHistoryExercise(WorkoutHistoryExerciseBase):
    id: int
    workout_history_id: int
    exercise: Exercise
    set_details: Optional[List[WorkoutHistoryExerciseSet]] = []

# WorkoutHistory schemas
class WorkoutHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str
    duration_minutes: int
    notes: Optional[str] = None
    rating: Optional[int] = None
    
    @field_validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class WorkoutHistoryCreate(WorkoutHistoryBase):
    workout_template_id: Optional[int] = None
    exercises: List[WorkoutHistoryExerciseCreate]

class WorkoutHistory(WorkoutHistoryBase):
    id: int
    user_id: int
    workout_template_id: Optional[int] = None
    date_completed: datetime
    exercises: List[WorkoutHistoryExercise]

# ScheduledWorkoutExerciseSet schemas
class ScheduledWorkoutExerciseSetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    set_number: int
    reps: int
    weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None

class ScheduledWorkoutExerciseSetCreate(ScheduledWorkoutExerciseSetBase):
    pass

class ScheduledWorkoutExerciseSet(ScheduledWorkoutExerciseSetBase):
    id: int
    scheduled_workout_exercise_id: int

# ScheduledWorkout schemas
class ScheduledWorkoutExerciseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    exercise_id: int
    sets: int
    reps: int
    weight: Optional[float] = None
    rest_time_seconds: Optional[int] = None
    notes: Optional[str] = None

class ScheduledWorkoutExerciseCreate(ScheduledWorkoutExerciseBase):
    set_details: Optional[List[ScheduledWorkoutExerciseSetCreate]] = None

class ScheduledWorkoutExercise(ScheduledWorkoutExerciseBase):
    id: int
    scheduled_workout_id: int
    exercise: Exercise
    set_details: Optional[List[ScheduledWorkoutExerciseSet]] = []

class ScheduledWorkoutBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str
    description: Optional[str] = None
    scheduled_date: datetime
    duration_minutes: int

class ScheduledWorkoutCreate(ScheduledWorkoutBase):
    workout_template_id: int
    exercises: Optional[List[ScheduledWorkoutExerciseCreate]] = None

class ScheduledWorkout(ScheduledWorkoutBase):
    id: int
    user_id: int
    workout_template_id: int
    is_completed: bool
    created_at: datetime
    exercises: List[ScheduledWorkoutExercise]

# TokenRequest schemas
class TokenRequestBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    amount: int
    reason: Optional[str] = None

class TokenRequestCreate(TokenRequestBase):
    pass

class TokenRequestUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: TokenRequestStatus
    
class TokenRequest(TokenRequestBase):
    id: int
    user_id: int
    status: TokenRequestStatus
    request_date: datetime
    response_date: Optional[datetime] = None
    approved_by_id: Optional[int] = None

# Token schemas
class TokenBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    amount: int
    transaction_type: TokenTransactionType
    description: Optional[str] = None
    request_id: Optional[int] = None
    workout_history_id: Optional[int] = None

class TokenCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    amount: int
    transaction_type: Optional[TokenTransactionType] = TokenTransactionType.SPEND
    description: Optional[str] = None
    request_id: Optional[int] = None
    workout_history_id: Optional[int] = None

class Token(TokenBase):
    id: int
    user_id: int
    timestamp: datetime

# User Token Balance
class UserTokenBalance(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    balance: int

# Authentication tokens (JWT)
class AuthToken(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 

# Notification schemas
class NotificationType(str, Enum):
    TOKEN_REQUEST = "token_request"
    TOKEN_APPROVED = "token_approved"
    TOKEN_REJECTED = "token_rejected"
    WORKOUT_COMPLETED = "workout_completed"
    NEW_EXERCISE = "new_exercise"
    ADMIN_NOTIFICATION = "admin_notification"
    SYSTEM_NOTIFICATION = "system_notification"

class NotificationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: NotificationType
    title: str
    message: str
    data: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime 