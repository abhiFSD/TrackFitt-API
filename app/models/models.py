from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, Enum, Index, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum
from datetime import datetime
from sqlalchemy import ARRAY
from typing import List, Optional
import datetime as dt

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    workouts = relationship("Workout", back_populates="user")
    workout_histories = relationship("WorkoutHistory", back_populates="user")
    scheduled_workouts = relationship("ScheduledWorkout", back_populates="user")
    token_requests = relationship("TokenRequest", back_populates="user", foreign_keys="TokenRequest.user_id")
    approved_requests = relationship("TokenRequest", back_populates="approved_by", foreign_keys="TokenRequest.approved_by_id")
    tokens = relationship("Token", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)

class ExerciseCategory(Base):
    __tablename__ = "exercise_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    exercises = relationship("Exercise", back_populates="category_relation")
    
class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)
    category_id = Column(Integer, ForeignKey("exercise_categories.id"), nullable=True)
    muscle_groups = Column(Text, nullable=True)
    difficulty = Column(String, nullable=True)
    equipment = Column(String, nullable=True)
    instructions = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    form_tips = Column(Text, nullable=True)
    common_mistakes = Column(Text, nullable=True)
    variations = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    category_relation = relationship("ExerciseCategory", back_populates="exercises")
    workout_exercises = relationship("WorkoutExercise", back_populates="exercise")
    workout_history_exercises = relationship("WorkoutHistoryExercise", back_populates="exercise")
    scheduled_workout_exercises = relationship("ScheduledWorkoutExercise", back_populates="exercise")

class Workout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    duration_minutes = Column(Integer)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_template = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="workouts")
    exercises = relationship("WorkoutExercise", back_populates="workout")
    workout_histories = relationship("WorkoutHistory", back_populates="workout_template")

class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"))
    exercise_id = Column(Integer, ForeignKey("exercises.id"))
    sets = Column(Integer)
    reps = Column(Integer)
    weight = Column(Float, nullable=True)
    rest_time_seconds = Column(Integer, nullable=True)  # Rest time after exercise in seconds
    notes = Column(Text, nullable=True)
    
    workout = relationship("Workout", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="workout_exercises")
    set_details = relationship("WorkoutExerciseSet", back_populates="workout_exercise", cascade="all, delete-orphan")

class WorkoutExerciseSet(Base):
    __tablename__ = "workout_exercise_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_exercise_id = Column(Integer, ForeignKey("workout_exercises.id"))
    set_number = Column(Integer)  # 1-based index
    reps = Column(Integer)
    weight = Column(Float, nullable=True)
    rest_time_seconds = Column(Integer, nullable=True)  # Rest time after this set
    
    workout_exercise = relationship("WorkoutExercise", back_populates="set_details")

class WorkoutHistory(Base):
    __tablename__ = "workout_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    workout_template_id = Column(Integer, ForeignKey("workouts.id"), nullable=True)
    title = Column(String, index=True)
    date_completed = Column(DateTime(timezone=True), server_default=func.now())
    duration_minutes = Column(Integer)
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    
    user = relationship("User", back_populates="workout_histories")
    workout_template = relationship("Workout", back_populates="workout_histories")
    exercises = relationship("WorkoutHistoryExercise", back_populates="workout_history")

class WorkoutHistoryExercise(Base):
    __tablename__ = "workout_history_exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_history_id = Column(Integer, ForeignKey("workout_histories.id"))
    exercise_id = Column(Integer, ForeignKey("exercises.id"))
    sets = Column(Integer)
    reps = Column(Integer)
    weight = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    
    workout_history = relationship("WorkoutHistory", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="workout_history_exercises")
    set_details = relationship("WorkoutHistoryExerciseSet", back_populates="workout_history_exercise", cascade="all, delete-orphan")

class WorkoutHistoryExerciseSet(Base):
    __tablename__ = "workout_history_exercise_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_history_exercise_id = Column(Integer, ForeignKey("workout_history_exercises.id"))
    set_number = Column(Integer)  # 1-based index
    planned_reps = Column(Integer)
    planned_weight = Column(Float, nullable=True)
    actual_reps = Column(Integer, nullable=True)
    actual_weight = Column(Float, nullable=True)
    rest_time_seconds = Column(Integer, nullable=True)  # Rest time after this set
    completion_time = Column(DateTime(timezone=True), nullable=True)  # When this set was completed
    duration_seconds = Column(Integer, nullable=True)  # Duration from workout start to set completion
    
    workout_history_exercise = relationship("WorkoutHistoryExercise", back_populates="set_details")

class ScheduledWorkout(Base):
    __tablename__ = "scheduled_workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    workout_template_id = Column(Integer, ForeignKey("workouts.id"))
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    scheduled_date = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="scheduled_workouts")
    workout_template = relationship("Workout", backref="scheduled_instances")
    exercises = relationship("ScheduledWorkoutExercise", back_populates="scheduled_workout", cascade="all, delete-orphan")

class ScheduledWorkoutExercise(Base):
    __tablename__ = "scheduled_workout_exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    scheduled_workout_id = Column(Integer, ForeignKey("scheduled_workouts.id"))
    exercise_id = Column(Integer, ForeignKey("exercises.id"))
    sets = Column(Integer)
    reps = Column(Integer)
    weight = Column(Float, nullable=True)
    rest_time_seconds = Column(Integer, nullable=True)  # Rest time after exercise in seconds
    notes = Column(Text, nullable=True)
    
    scheduled_workout = relationship("ScheduledWorkout", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="scheduled_workout_exercises")
    set_details = relationship("ScheduledWorkoutExerciseSet", back_populates="scheduled_workout_exercise", cascade="all, delete-orphan")

class ScheduledWorkoutExerciseSet(Base):
    __tablename__ = "scheduled_workout_exercise_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    scheduled_workout_exercise_id = Column(Integer, ForeignKey("scheduled_workout_exercises.id"))
    set_number = Column(Integer)  # 1-based index
    reps = Column(Integer)
    weight = Column(Float, nullable=True)
    rest_time_seconds = Column(Integer, nullable=True)  # Rest time after this set
    
    scheduled_workout_exercise = relationship("ScheduledWorkoutExercise", back_populates="set_details")

class TokenRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TokenRequest(Base):
    __tablename__ = "token_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)
    reason = Column(Text, nullable=True)
    status = Column(Enum(TokenRequestStatus), default=TokenRequestStatus.PENDING)
    request_date = Column(DateTime(timezone=True), server_default=func.now())
    response_date = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    user = relationship("User", back_populates="token_requests", foreign_keys=[user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

class TokenTransactionType(enum.Enum):
    EARN = "earn"
    SPEND = "spend"
    ADMIN_ADJUSTMENT = "admin_adjustment"

class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)
    transaction_type = Column(Enum(TokenTransactionType))
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    request_id = Column(Integer, ForeignKey("token_requests.id"), nullable=True)
    workout_history_id = Column(Integer, ForeignKey("workout_histories.id"), nullable=True)
    
    user = relationship("User", back_populates="tokens")
    token_request = relationship("TokenRequest", foreign_keys=[request_id])
    workout_history = relationship("WorkoutHistory", foreign_keys=[workout_history_id])

class FitnessLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"

class ActivityLevel(str, enum.Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Basic Information
    first_name = Column(String)
    last_name = Column(String)
    birth_date = Column(Date, nullable=True)
    gender = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    
    # Physical Metrics
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    body_fat_percentage = Column(Float, nullable=True)
    
    # Fitness Data
    fitness_level = Column(Enum(FitnessLevel), default=FitnessLevel.BEGINNER)
    activity_level = Column(Enum(ActivityLevel), default=ActivityLevel.MODERATELY_ACTIVE)
    
    # Goals
    weight_goal_kg = Column(Float, nullable=True)
    weekly_workout_goal = Column(Integer, default=3)  # Number of workouts per week
    
    # Preferences
    preferred_workout_duration = Column(Integer, default=45)  # in minutes
    preferred_workout_days = Column(ARRAY(String), default=[])
    favorite_muscle_groups = Column(ARRAY(String), default=[])
    
    # Health Data
    has_injuries = Column(Boolean, default=False)
    injury_notes = Column(String, nullable=True)
    has_medical_conditions = Column(Boolean, default=False)
    medical_notes = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship
    user = relationship("User", back_populates="profile")
    
    __table_args__ = (
        Index('idx_user_profile_user_id', user_id),
    ) 

class NotificationType(str, enum.Enum):
    TOKEN_REQUEST = "token_request"
    TOKEN_APPROVED = "token_approved"
    TOKEN_REJECTED = "token_rejected"
    WORKOUT_COMPLETED = "workout_completed"
    NEW_EXERCISE = "new_exercise"
    ADMIN_NOTIFICATION = "admin_notification"
    SYSTEM_NOTIFICATION = "system_notification"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(Enum(NotificationType))
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON data related to the notification
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="notifications")
    
    __table_args__ = (
        Index('idx_notification_user_id', user_id),
    ) 

class AIOperationType(str, enum.Enum):
    WORKOUT_CREATION = "workout_creation"
    DIET_RECOMMENDATION = "diet_recommendation"
    FITNESS_ADVICE = "fitness_advice"
    PROGRESS_ANALYSIS = "progress_analysis"

class AITracking(Base):
    __tablename__ = "ai_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    operation_type = Column(Enum(AIOperationType))
    user_prompt = Column(Text, nullable=False)
    input_data = Column(Text, nullable=True)  # JSON string of input data
    response_data = Column(Text, nullable=True)  # JSON string of AI response
    status = Column(String, nullable=False, default="completed")
    duration_ms = Column(Integer, nullable=True)  # Processing time in milliseconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    extra_data = Column(Text, nullable=True)  # Additional metadata as JSON
    
    user = relationship("User", backref="ai_operations")
    
    __table_args__ = (
        Index('idx_ai_tracking_user_id', user_id),
        Index('idx_ai_tracking_operation_type', operation_type),
    ) 