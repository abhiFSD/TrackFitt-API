from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, select, text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
import boto3
from uuid import uuid4
from sqlalchemy.sql import or_, and_

from app.db.database import get_db
from app.models.models import (
    User as DBUser, Exercise as DBExercise, Workout as DBWorkout, WorkoutExercise as DBWorkoutExercise, 
    WorkoutHistory as DBWorkoutHistory, WorkoutHistoryExercise as DBWorkoutHistoryExercise,
    TokenRequest as DBTokenRequest, TokenRequestStatus, Token as DBToken,
    TokenTransactionType, UserRole as DBUserRole, UserProfile as DBUserProfile,
    FitnessLevel, ActivityLevel, NotificationType as DBNotificationType,
    ScheduledWorkout as DBScheduledWorkout, ScheduledWorkoutExercise as DBScheduledWorkoutExercise,
    WorkoutExerciseSet as DBWorkoutExerciseSet, WorkoutHistoryExerciseSet as DBWorkoutHistoryExerciseSet
)
from app.schemas.schemas import (
    User, UserCreate, Exercise, ExerciseCreate,
    Workout, WorkoutCreate, WorkoutHistory, WorkoutHistoryCreate,
    TokenRequest, TokenRequestCreate, TokenRequestUpdate,
    Token, TokenCreate, UserTokenBalance, AuthToken, UserRole, 
    TokenTransactionType as SchemaTokenTransactionType,
    TokenRequestStatus as SchemaTokenRequestStatus,
    UserProfile, UserProfileCreate, UserProfileUpdate, UserWithProfile,
    Notification, ScheduledWorkout, ScheduledWorkoutCreate,
    ExerciseCategory, ExerciseCategoryCreate
)
from app.api.auth import (
    authenticate_user, create_access_token, get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user, get_current_admin_user
)
from app.services.notification_service import NotificationService
from app.services.notification_manager import NotificationManager

router = APIRouter()

# Authentication routes
@router.post("/token", response_model=AuthToken)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Helper function to convert DB model to schema
def convert_user_to_schema(user: DBUser) -> User:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "role": UserRole(user.role.value),
        "created_at": user.created_at
    }

# Helper function to convert DBToken to Token schema
def convert_token_to_schema(token: DBToken) -> Token:
    return {
        "id": token.id,
        "user_id": token.user_id,
        "amount": token.amount,
        "transaction_type": SchemaTokenTransactionType(token.transaction_type.value),
        "description": token.description,
        "request_id": token.request_id,
        "workout_history_id": token.workout_history_id,
        "timestamp": token.timestamp
    }

# Helper function to convert DBTokenRequest to TokenRequest schema
def convert_token_request_to_schema(token_request: DBTokenRequest) -> TokenRequest:
    return {
        "id": token_request.id,
        "user_id": token_request.user_id,
        "amount": token_request.amount,
        "reason": token_request.reason,
        "status": SchemaTokenRequestStatus(token_request.status.value),
        "request_date": token_request.request_date,
        "response_date": token_request.response_date,
        "approved_by_id": token_request.approved_by_id
    }

# User routes
@router.post("/users/", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(DBUser).filter(DBUser.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(DBUser).filter(DBUser.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = DBUser(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=DBUserRole(user.role)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return convert_user_to_schema(db_user)

@router.get("/users/me/", response_model=UserWithProfile)
def read_users_me(db: Session = Depends(get_db), current_user: DBUser = Depends(get_current_active_user)):
    # Fetch the user with their profile
    db_user = db.query(DBUser).options(joinedload(DBUser.profile)).filter(DBUser.id == current_user.id).first()
    
    user_data = convert_user_to_schema(db_user)
    
    # Include profile if it exists
    if db_user.profile:
        user_data["profile"] = {
            "id": db_user.profile.id,
            "user_id": db_user.profile.user_id,
            "first_name": db_user.profile.first_name,
            "last_name": db_user.profile.last_name,
            "birth_date": db_user.profile.birth_date,
            "gender": db_user.profile.gender,
            "profile_image_url": db_user.profile.profile_image_url,
            "height_cm": db_user.profile.height_cm,
            "weight_kg": db_user.profile.weight_kg,
            "body_fat_percentage": db_user.profile.body_fat_percentage,
            "fitness_level": db_user.profile.fitness_level.value if db_user.profile.fitness_level else None,
            "activity_level": db_user.profile.activity_level.value if db_user.profile.activity_level else None,
            "weight_goal_kg": db_user.profile.weight_goal_kg,
            "weekly_workout_goal": db_user.profile.weekly_workout_goal,
            "preferred_workout_duration": db_user.profile.preferred_workout_duration,
            "preferred_workout_days": db_user.profile.preferred_workout_days,
            "favorite_muscle_groups": db_user.profile.favorite_muscle_groups,
            "has_injuries": db_user.profile.has_injuries,
            "injury_notes": db_user.profile.injury_notes,
            "has_medical_conditions": db_user.profile.has_medical_conditions,
            "medical_notes": db_user.profile.medical_notes,
            "created_at": db_user.profile.created_at,
            "updated_at": db_user.profile.updated_at
        }
    
    return user_data

@router.get("/users/", response_model=List[User])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    users = db.query(DBUser).offset(skip).limit(limit).all()
    return [convert_user_to_schema(user) for user in users]

# Enhanced Admin User Management routes
@router.get("/admin/users/", response_model=List[UserWithProfile])
def admin_get_users(
    skip: int = 0,
    limit: int = 100,
    username: Optional[str] = None,
    email: Optional[str] = None,
    is_active: Optional[bool] = None,
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    """
    Get all users with optional filtering parameters.
    Only accessible by admins.
    """
    query = db.query(DBUser).options(joinedload(DBUser.profile))
    
    # Apply filters if provided
    if username:
        query = query.filter(DBUser.username.ilike(f"%{username}%"))
    if email:
        query = query.filter(DBUser.email.ilike(f"%{email}%"))
    if is_active is not None:
        query = query.filter(DBUser.is_active == is_active)
    if role:
        query = query.filter(DBUser.role == DBUserRole(role))
    
    users = query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        user_data = convert_user_to_schema(user)
        
        # Include profile if it exists
        if user.profile:
            user_data["profile"] = {
                "id": user.profile.id,
                "user_id": user.profile.user_id,
                "first_name": user.profile.first_name,
                "last_name": user.profile.last_name,
                "birth_date": user.profile.birth_date,
                "gender": user.profile.gender,
                "profile_image_url": user.profile.profile_image_url,
                "height_cm": user.profile.height_cm,
                "weight_kg": user.profile.weight_kg,
                "body_fat_percentage": user.profile.body_fat_percentage,
                "fitness_level": user.profile.fitness_level.value if user.profile.fitness_level else None,
                "activity_level": user.profile.activity_level.value if user.profile.activity_level else None,
                "weight_goal_kg": user.profile.weight_goal_kg,
                "weekly_workout_goal": user.profile.weekly_workout_goal,
                "preferred_workout_duration": user.profile.preferred_workout_duration,
                "preferred_workout_days": user.profile.preferred_workout_days,
                "favorite_muscle_groups": user.profile.favorite_muscle_groups,
                "has_injuries": user.profile.has_injuries,
                "injury_notes": user.profile.injury_notes,
                "has_medical_conditions": user.profile.has_medical_conditions,
                "medical_notes": user.profile.medical_notes,
                "created_at": user.profile.created_at,
                "updated_at": user.profile.updated_at
            }
        
        result.append(user_data)
    
    return result

@router.get("/admin/users/{user_id}", response_model=UserWithProfile)
def admin_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    """
    Get a specific user by ID.
    Only accessible by admins.
    """
    db_user = db.query(DBUser).options(joinedload(DBUser.profile)).filter(DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = convert_user_to_schema(db_user)
    
    # Include profile if it exists
    if db_user.profile:
        user_data["profile"] = {
            "id": db_user.profile.id,
            "user_id": db_user.profile.user_id,
            "first_name": db_user.profile.first_name,
            "last_name": db_user.profile.last_name,
            "birth_date": db_user.profile.birth_date,
            "gender": db_user.profile.gender,
            "profile_image_url": db_user.profile.profile_image_url,
            "height_cm": db_user.profile.height_cm,
            "weight_kg": db_user.profile.weight_kg,
            "body_fat_percentage": db_user.profile.body_fat_percentage,
            "fitness_level": db_user.profile.fitness_level.value if db_user.profile.fitness_level else None,
            "activity_level": db_user.profile.activity_level.value if db_user.profile.activity_level else None,
            "weight_goal_kg": db_user.profile.weight_goal_kg,
            "weekly_workout_goal": db_user.profile.weekly_workout_goal,
            "preferred_workout_duration": db_user.profile.preferred_workout_duration,
            "preferred_workout_days": db_user.profile.preferred_workout_days,
            "favorite_muscle_groups": db_user.profile.favorite_muscle_groups,
            "has_injuries": db_user.profile.has_injuries,
            "injury_notes": db_user.profile.injury_notes,
            "has_medical_conditions": db_user.profile.has_medical_conditions,
            "medical_notes": db_user.profile.medical_notes,
            "created_at": db_user.profile.created_at,
            "updated_at": db_user.profile.updated_at
        }
    
    return user_data

class UserStatusUpdate(BaseModel):
    is_active: bool

@router.patch("/admin/users/{user_id}/status", response_model=User)
def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    """
    Update a user's active status.
    Only accessible by admins.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot update your own status")
    
    db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_active = status_update.is_active
    db.commit()
    db.refresh(db_user)
    
    return convert_user_to_schema(db_user)

class UserRoleUpdate(BaseModel):
    role: UserRole

@router.patch("/admin/users/{user_id}/role", response_model=User)
def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    """
    Update a user's role.
    Only accessible by admins.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot update your own role")
    
    db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.role = DBUserRole(role_update.role)
    db.commit()
    db.refresh(db_user)
    
    return convert_user_to_schema(db_user)

@router.delete("/admin/users/{user_id}", response_model=Dict[str, bool])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    """
    Delete a user account.
    Only accessible by admins.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user
    db.delete(db_user)
    db.commit()
    
    return {"success": True}

# User Profile routes
@router.post("/users/profile/", response_model=UserProfile)
def create_or_update_user_profile(
    profile: UserProfileCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Check if user already has a profile
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == current_user.id).first()
    
    if db_profile:
        # Update existing profile
        for key, value in profile.dict(exclude_unset=True).items():
            if key in ['fitness_level', 'activity_level'] and value is not None:
                # Handle enum values
                if key == 'fitness_level':
                    value = FitnessLevel(value)
                elif key == 'activity_level':
                    value = ActivityLevel(value)
            setattr(db_profile, key, value)
        
        db_profile.updated_at = datetime.now()
    else:
        # Create new profile
        profile_data = profile.dict(exclude_unset=True)
        
        # Convert string enums to actual enum values
        if 'fitness_level' in profile_data and profile_data['fitness_level']:
            profile_data['fitness_level'] = FitnessLevel(profile_data['fitness_level'])
        
        if 'activity_level' in profile_data and profile_data['activity_level']:
            profile_data['activity_level'] = ActivityLevel(profile_data['activity_level'])
        
        db_profile = DBUserProfile(user_id=current_user.id, **profile_data)
        db.add(db_profile)
    
    db.commit()
    db.refresh(db_profile)
    
    return {
        "id": db_profile.id,
        "user_id": db_profile.user_id,
        "first_name": db_profile.first_name,
        "last_name": db_profile.last_name,
        "birth_date": db_profile.birth_date,
        "gender": db_profile.gender,
        "profile_image_url": db_profile.profile_image_url,
        "height_cm": db_profile.height_cm,
        "weight_kg": db_profile.weight_kg,
        "body_fat_percentage": db_profile.body_fat_percentage,
        "fitness_level": db_profile.fitness_level.value if db_profile.fitness_level else None,
        "activity_level": db_profile.activity_level.value if db_profile.activity_level else None,
        "weight_goal_kg": db_profile.weight_goal_kg,
        "weekly_workout_goal": db_profile.weekly_workout_goal,
        "preferred_workout_duration": db_profile.preferred_workout_duration,
        "preferred_workout_days": db_profile.preferred_workout_days,
        "favorite_muscle_groups": db_profile.favorite_muscle_groups,
        "has_injuries": db_profile.has_injuries,
        "injury_notes": db_profile.injury_notes,
        "has_medical_conditions": db_profile.has_medical_conditions,
        "medical_notes": db_profile.medical_notes,
        "created_at": db_profile.created_at,
        "updated_at": db_profile.updated_at
    }

@router.get("/users/profile/", response_model=UserProfile)
def read_user_profile(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == current_user.id).first()
    
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "id": db_profile.id,
        "user_id": db_profile.user_id,
        "first_name": db_profile.first_name,
        "last_name": db_profile.last_name,
        "birth_date": db_profile.birth_date,
        "gender": db_profile.gender,
        "profile_image_url": db_profile.profile_image_url,
        "height_cm": db_profile.height_cm,
        "weight_kg": db_profile.weight_kg,
        "body_fat_percentage": db_profile.body_fat_percentage,
        "fitness_level": db_profile.fitness_level.value if db_profile.fitness_level else None,
        "activity_level": db_profile.activity_level.value if db_profile.activity_level else None,
        "weight_goal_kg": db_profile.weight_goal_kg,
        "weekly_workout_goal": db_profile.weekly_workout_goal,
        "preferred_workout_duration": db_profile.preferred_workout_duration,
        "preferred_workout_days": db_profile.preferred_workout_days,
        "favorite_muscle_groups": db_profile.favorite_muscle_groups,
        "has_injuries": db_profile.has_injuries,
        "injury_notes": db_profile.injury_notes,
        "has_medical_conditions": db_profile.has_medical_conditions,
        "medical_notes": db_profile.medical_notes,
        "created_at": db_profile.created_at,
        "updated_at": db_profile.updated_at
    }

@router.put("/users/profile/", response_model=UserProfile)
def update_user_profile(
    profile: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == current_user.id).first()
    
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Update fields
    for key, value in profile.dict(exclude_unset=True).items():
        if key in ['fitness_level', 'activity_level'] and value is not None:
            # Handle enum values
            if key == 'fitness_level':
                value = FitnessLevel(value)
            elif key == 'activity_level':
                value = ActivityLevel(value)
        setattr(db_profile, key, value)
    
    db_profile.updated_at = datetime.now()
    db.commit()
    db.refresh(db_profile)
    
    return {
        "id": db_profile.id,
        "user_id": db_profile.user_id,
        "first_name": db_profile.first_name,
        "last_name": db_profile.last_name,
        "birth_date": db_profile.birth_date,
        "gender": db_profile.gender,
        "profile_image_url": db_profile.profile_image_url,
        "height_cm": db_profile.height_cm,
        "weight_kg": db_profile.weight_kg,
        "body_fat_percentage": db_profile.body_fat_percentage,
        "fitness_level": db_profile.fitness_level.value if db_profile.fitness_level else None,
        "activity_level": db_profile.activity_level.value if db_profile.activity_level else None,
        "weight_goal_kg": db_profile.weight_goal_kg,
        "weekly_workout_goal": db_profile.weekly_workout_goal,
        "preferred_workout_duration": db_profile.preferred_workout_duration,
        "preferred_workout_days": db_profile.preferred_workout_days,
        "favorite_muscle_groups": db_profile.favorite_muscle_groups,
        "has_injuries": db_profile.has_injuries,
        "injury_notes": db_profile.injury_notes,
        "has_medical_conditions": db_profile.has_medical_conditions,
        "medical_notes": db_profile.medical_notes,
        "created_at": db_profile.created_at,
        "updated_at": db_profile.updated_at
    }

@router.get("/users/profile/completion", response_model=Dict[str, Any])
def get_profile_completion(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == current_user.id).first()
    
    if not db_profile:
        return {
            "is_complete": False,
            "completion_percentage": 0,
            "sections": {
                "basic_information": {
                    "is_complete": False,
                    "missing_fields": ["first_name", "last_name", "birth_date", "gender"]
                },
                "physical_metrics": {
                    "is_complete": False,
                    "missing_fields": ["height_cm", "weight_kg"]
                },
                "fitness_data": {
                    "is_complete": False,
                    "missing_fields": ["fitness_level", "activity_level"]
                },
                "goals": {
                    "is_complete": False,
                    "missing_fields": ["weekly_workout_goal"]
                },
                "preferences": {
                    "is_complete": False,
                    "missing_fields": ["preferred_workout_days", "favorite_muscle_groups"]
                }
            }
        }
    
    # Check completion of each section
    sections = {}
    
    # Basic Information
    basic_info_fields = ["first_name", "last_name", "birth_date", "gender"]
    basic_info_missing = [field for field in basic_info_fields if getattr(db_profile, field) is None]
    sections["basic_information"] = {
        "is_complete": len(basic_info_missing) == 0,
        "missing_fields": basic_info_missing
    }
    
    # Physical Metrics
    physical_metrics_fields = ["height_cm", "weight_kg"]
    physical_metrics_missing = [field for field in physical_metrics_fields if getattr(db_profile, field) is None]
    sections["physical_metrics"] = {
        "is_complete": len(physical_metrics_missing) == 0,
        "missing_fields": physical_metrics_missing
    }
    
    # Fitness Data
    fitness_data_fields = ["fitness_level", "activity_level"]
    fitness_data_missing = [field for field in fitness_data_fields if getattr(db_profile, field) is None]
    sections["fitness_data"] = {
        "is_complete": len(fitness_data_missing) == 0,
        "missing_fields": fitness_data_missing
    }
    
    # Goals
    goals_fields = ["weekly_workout_goal"]
    goals_missing = [field for field in goals_fields if getattr(db_profile, field) is None]
    sections["goals"] = {
        "is_complete": len(goals_missing) == 0,
        "missing_fields": goals_missing
    }
    
    # Preferences
    preferences_fields = ["preferred_workout_days", "favorite_muscle_groups"]
    preferences_missing = []
    if not db_profile.preferred_workout_days or len(db_profile.preferred_workout_days) == 0:
        preferences_missing.append("preferred_workout_days")
    if not db_profile.favorite_muscle_groups or len(db_profile.favorite_muscle_groups) == 0:
        preferences_missing.append("favorite_muscle_groups")
    
    sections["preferences"] = {
        "is_complete": len(preferences_missing) == 0,
        "missing_fields": preferences_missing
    }
    
    # Calculate overall completion
    total_fields = len(basic_info_fields) + len(physical_metrics_fields) + len(fitness_data_fields) + len(goals_fields) + len(preferences_fields)
    missing_fields = len(basic_info_missing) + len(physical_metrics_missing) + len(fitness_data_missing) + len(goals_missing) + len(preferences_missing)
    
    completion_percentage = round(((total_fields - missing_fields) / total_fields) * 100) if total_fields > 0 else 0
    
    return {
        "is_complete": missing_fields == 0,
        "completion_percentage": completion_percentage,
        "sections": sections
    }

# Exercise Category routes
@router.post("/exercise-categories/", response_model=ExerciseCategory)
def create_exercise_category(
    category: ExerciseCategoryCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Check if category already exists
    existing_category = db.query(DBExerciseCategory).filter(DBExerciseCategory.name == category.name).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    db_category = DBExerciseCategory(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/exercise-categories/", response_model=List[ExerciseCategory])
def get_exercise_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    categories = db.query(DBExerciseCategory).offset(skip).limit(limit).all()
    return categories

@router.get("/exercise-categories/{category_id}", response_model=ExerciseCategory)
def get_exercise_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    category = db.query(DBExerciseCategory).filter(DBExerciseCategory.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.put("/exercise-categories/{category_id}", response_model=ExerciseCategory)
def update_exercise_category(
    category_id: int,
    category: ExerciseCategoryCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    db_category = db.query(DBExerciseCategory).filter(DBExerciseCategory.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    for key, value in category.dict().items():
        setattr(db_category, key, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/exercise-categories/{category_id}", response_model=Dict[str, bool])
def delete_exercise_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    db_category = db.query(DBExerciseCategory).filter(DBExerciseCategory.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if any exercises are using this category
    exercises_with_category = db.query(DBExercise).filter(DBExercise.category_id == category_id).count()
    if exercises_with_category > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category as it is being used by {exercises_with_category} exercises"
        )
    
    db.delete(db_category)
    db.commit()
    return {"success": True}

# Exercise routes
@router.post("/exercises/", response_model=Exercise)
def create_exercise(
    exercise: ExerciseCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Check if exercise already exists
    existing_exercise = db.query(DBExercise).filter(DBExercise.name == exercise.name).first()
    if existing_exercise:
        raise HTTPException(status_code=400, detail="Exercise with this name already exists")

    # Check if category_id is provided and exists
    if exercise.category_id:
        category = db.query(DBExerciseCategory).filter(DBExerciseCategory.id == exercise.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Specified category does not exist")
        
        # Set the category name for backward compatibility
        exercise.category = category.name

    db_exercise = DBExercise(**exercise.dict())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.get("/exercises/", response_model=List[Exercise])
def read_exercises(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    category_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    equipment: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    query = db.query(DBExercise)
    
    if category:
        query = query.filter(DBExercise.category == category)
    
    if category_id:
        query = query.filter(DBExercise.category_id == category_id)
    
    if difficulty:
        query = query.filter(DBExercise.difficulty == difficulty)
    
    if equipment:
        query = query.filter(DBExercise.equipment.ilike(f"%{equipment}%"))
    
    if search:
        query = query.filter(
            or_(
                DBExercise.name.ilike(f"%{search}%"),
                DBExercise.description.ilike(f"%{search}%")
            )
        )
    
    exercises = query.offset(skip).limit(limit).all()
    return exercises

@router.get("/exercises/categories", response_model=List[str])
def get_legacy_exercise_categories(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    categories = db.query(DBExercise.category).distinct().all()
    return [category[0] for category in categories if category[0]]

@router.get("/exercises/{exercise_id}", response_model=Exercise)
def read_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    exercise = db.query(DBExercise).filter(DBExercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise

@router.put("/exercises/{exercise_id}", response_model=Exercise)
def update_exercise(
    exercise_id: int,
    exercise: ExerciseCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    db_exercise = db.query(DBExercise).filter(DBExercise.id == exercise_id).first()
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Check if category_id is provided and exists
    if exercise.category_id:
        category = db.query(DBExerciseCategory).filter(DBExerciseCategory.id == exercise.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Specified category does not exist")
        
        # Set the category name for backward compatibility
        exercise.category = category.name
    
    for key, value in exercise.dict().items():
        setattr(db_exercise, key, value)
    
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

# Workout routes
@router.post("/workouts/", response_model=Workout)
def create_workout(
    workout: WorkoutCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Create workout
    db_workout = DBWorkout(
        title=workout.title,
        description=workout.description,
        duration_minutes=workout.duration_minutes,
        is_template=workout.is_template,
        is_published=workout.is_published,
        user_id=current_user.id
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    
    # Add exercises to workout
    for exercise_data in workout.exercises:
        # Extract set_details before creating the workout exercise
        set_details = exercise_data.dict().pop("set_details", None)
        
        # Create the workout exercise
        db_workout_exercise = DBWorkoutExercise(
            workout_id=db_workout.id,
            **exercise_data.dict(exclude={"set_details"})
        )
        db.add(db_workout_exercise)
        db.commit()
        db.refresh(db_workout_exercise)
        
        # Add set details if they exist
        if set_details:
            for set_data in set_details:
                db_set = DBWorkoutExerciseSet(
                    workout_exercise_id=db_workout_exercise.id,
                    **set_data
                )
                db.add(db_set)
    
    db.commit()
    db.refresh(db_workout)
    return db_workout

@router.get("/workouts/", response_model=List[Workout])
def read_workouts(
    skip: int = 0,
    limit: int = 100,
    is_template: Optional[bool] = None,
    public: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    if public:
        # Get all public workouts (is_published=True) from all users
        query = db.query(DBWorkout).filter(DBWorkout.is_published == True)
    else:
        # Get only the current user's workouts
        query = db.query(DBWorkout).filter(DBWorkout.user_id == current_user.id)
        
    if is_template is not None:
        query = query.filter(DBWorkout.is_template == is_template)
    
    workouts = query.offset(skip).limit(limit).all()
    return workouts

@router.get("/workouts/{workout_id}", response_model=Workout)
def read_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    workout = db.query(DBWorkout).filter(
        DBWorkout.id == workout_id,
        DBWorkout.user_id == current_user.id
    ).first()
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout

@router.patch("/workouts/{workout_id}/publish", response_model=Workout)
def publish_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    workout = db.query(DBWorkout).filter(
        DBWorkout.id == workout_id,
        DBWorkout.user_id == current_user.id
    ).first()
    
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    workout.is_published = True
    db.commit()
    db.refresh(workout)
    return workout

# Workout History routes
@router.post("/workout-history/", response_model=WorkoutHistory)
async def record_workout_history(
    workout_history: WorkoutHistoryCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Create workout history entry
    db_workout_history = DBWorkoutHistory(
        user_id=current_user.id,
        workout_template_id=workout_history.workout_template_id,
        title=workout_history.title,
        duration_minutes=workout_history.duration_minutes,
        notes=workout_history.notes,
        rating=workout_history.rating
    )
    db.add(db_workout_history)
    db.commit()
    db.refresh(db_workout_history)
    
    # Add exercises to workout history
    for exercise_data in workout_history.exercises:
        # Extract set_details before creating the workout history exercise
        set_details = exercise_data.dict().pop("set_details", None)
        
        # Create the workout history exercise - explicitly exclude rest_time_seconds
        exercise_dict = exercise_data.dict(exclude={"set_details", "rest_time_seconds"})
        db_workout_history_exercise = DBWorkoutHistoryExercise(
            workout_history_id=db_workout_history.id,
            **exercise_dict
        )
        db.add(db_workout_history_exercise)
        db.commit()
        db.refresh(db_workout_history_exercise)
        
        # Add set details if they exist
        if set_details:
            for set_data in set_details:
                db_set = DBWorkoutHistoryExerciseSet(
                    workout_history_exercise_id=db_workout_history_exercise.id,
                    **set_data
                )
                db.add(db_set)
    
    db.commit()
    db.refresh(db_workout_history)
    
    # Award tokens for completing a workout (if appropriate)
    token_amount = 10  # Default amount for completing a workout
    
    db_token = DBToken(
        user_id=current_user.id,
        amount=token_amount,
        transaction_type=TokenTransactionType.EARN,
        description="Completed workout: " + workout_history.title,
        workout_history_id=db_workout_history.id
    )
    db.add(db_token)
    db.commit()
    
    # Send notification about completed workout and tokens earned
    await NotificationManager.notify_workout_completed(
        db=db,
        user_id=current_user.id,
        workout_history_id=db_workout_history.id,
        title=workout_history.title,
        tokens_earned=token_amount
    )
    
    return db_workout_history

@router.get("/workout-history/", response_model=List[WorkoutHistory])
def read_workout_history(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    query = db.query(DBWorkoutHistory).filter(DBWorkoutHistory.user_id == current_user.id)
    
    if start_date:
        query = query.filter(DBWorkoutHistory.date_completed >= start_date)
    if end_date:
        query = query.filter(DBWorkoutHistory.date_completed <= end_date)
    
    workout_histories = query.order_by(DBWorkoutHistory.date_completed.desc()).offset(skip).limit(limit).all()
    return workout_histories

@router.get("/workout-history/{history_id}", response_model=WorkoutHistory)
def read_workout_history_entry(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    workout_history = db.query(DBWorkoutHistory).filter(
        DBWorkoutHistory.id == history_id,
        DBWorkoutHistory.user_id == current_user.id
    ).first()
    if workout_history is None:
        raise HTTPException(status_code=404, detail="Workout history entry not found")
    return workout_history

# Add this model for workout history updates
class WorkoutHistoryUpdate(BaseModel):
    title: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    rating: Optional[int] = None

# Add this endpoint after the other workout history routes
@router.patch("/workout-history/{history_id}", response_model=WorkoutHistory)
def update_workout_history(
    history_id: int,
    workout_update: WorkoutHistoryUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    workout_history = db.query(DBWorkoutHistory).filter(
        DBWorkoutHistory.id == history_id,
        DBWorkoutHistory.user_id == current_user.id
    ).first()
    
    if workout_history is None:
        raise HTTPException(status_code=404, detail="Workout history entry not found")
    
    # Update only the provided fields
    if workout_update.title is not None:
        workout_history.title = workout_update.title
    
    if workout_update.duration_minutes is not None:
        workout_history.duration_minutes = workout_update.duration_minutes
    
    if workout_update.notes is not None:
        workout_history.notes = workout_update.notes
    
    if workout_update.rating is not None:
        workout_history.rating = workout_update.rating
    
    db.commit()
    db.refresh(workout_history)
    
    return workout_history

# New model for updating set completion data
class SetCompletionUpdate(BaseModel):
    set_number: int
    actual_reps: Optional[int] = None
    actual_weight: Optional[float] = None
    completion_time: Optional[str] = None
    duration_seconds: Optional[int] = None

@router.patch("/workout-history/{history_id}/exercise/{exercise_index}/set", response_model=Dict[str, Any])
def update_set_completion(
    history_id: int,
    exercise_index: int,
    set_data: SetCompletionUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # First verify the workout history belongs to the user
    workout_history = db.query(DBWorkoutHistory).filter(
        DBWorkoutHistory.id == history_id,
        DBWorkoutHistory.user_id == current_user.id
    ).first()
    
    if not workout_history:
        raise HTTPException(status_code=404, detail="Workout history not found")
    
    # Get all exercises for this workout history
    exercises = db.query(DBWorkoutHistoryExercise).filter(
        DBWorkoutHistoryExercise.workout_history_id == history_id
    ).all()
    
    if exercise_index < 0 or exercise_index >= len(exercises):
        raise HTTPException(status_code=404, detail="Exercise index out of range")
    
    # Get the selected exercise
    exercise = exercises[exercise_index]
    
    # Find the set with the matching set number
    db_set = db.query(DBWorkoutHistoryExerciseSet).filter(
        DBWorkoutHistoryExerciseSet.workout_history_exercise_id == exercise.id,
        DBWorkoutHistoryExerciseSet.set_number == set_data.set_number
    ).first()
    
    if not db_set:
        raise HTTPException(status_code=404, detail="Set not found")
    
    # Update the set with the new data
    if set_data.actual_reps is not None:
        db_set.actual_reps = set_data.actual_reps
    
    if set_data.actual_weight is not None:
        db_set.actual_weight = set_data.actual_weight
    
    if set_data.completion_time is not None:
        db_set.completion_time = datetime.fromisoformat(set_data.completion_time.replace('Z', '+00:00'))
    
    if set_data.duration_seconds is not None:
        db_set.duration_seconds = set_data.duration_seconds
    
    db.commit()
    db.refresh(db_set)
    
    return {
        "success": True,
        "message": f"Set {set_data.set_number} updated successfully",
        "set_data": {
            "set_number": db_set.set_number,
            "actual_reps": db_set.actual_reps,
            "actual_weight": db_set.actual_weight,
            "completion_time": db_set.completion_time,
            "duration_seconds": db_set.duration_seconds
        }
    }

# Token Request routes
@router.post("/token-requests/", response_model=TokenRequest)
async def create_token_request(
    token_request: TokenRequestCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    db_token_request = DBTokenRequest(
        user_id=current_user.id,
        amount=token_request.amount,
        reason=token_request.reason,
        status=TokenRequestStatus.PENDING,
        request_date=datetime.now()
    )
    db.add(db_token_request)
    db.commit()
    db.refresh(db_token_request)
    
    # Send notification to admins about the new token request
    await NotificationManager.notify_token_request(
        db=db, 
        request_id=db_token_request.id, 
        user_id=current_user.id, 
        amount=token_request.amount, 
        reason=token_request.reason
    )
    
    return convert_token_request_to_schema(db_token_request)

@router.get("/token-requests/", response_model=List[TokenRequest])
def read_token_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TokenRequestStatus] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    if current_user.role == DBUserRole.ADMIN:
        # Admins can see all requests
        query = db.query(DBTokenRequest)
        if status:
            query = query.filter(DBTokenRequest.status == status)
        token_requests = query.order_by(DBTokenRequest.request_date.desc()).offset(skip).limit(limit).all()
    else:
        # Users can only see their own requests
        query = db.query(DBTokenRequest).filter(DBTokenRequest.user_id == current_user.id)
        if status:
            query = query.filter(DBTokenRequest.status == status)
        token_requests = query.order_by(DBTokenRequest.request_date.desc()).offset(skip).limit(limit).all()
    
    return [convert_token_request_to_schema(req) for req in token_requests]

@router.put("/token-requests/{request_id}", response_model=TokenRequest)
async def update_token_request(
    request_id: int,
    token_request_update: TokenRequestUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    db_token_request = db.query(DBTokenRequest).filter(DBTokenRequest.id == request_id).first()
    if db_token_request is None:
        raise HTTPException(status_code=404, detail="Token request not found")
    
    # Only pending requests can be updated
    if db_token_request.status != TokenRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending requests can be updated")
    
    # Convert the schema enum to database enum
    db_status = TokenRequestStatus(token_request_update.status)
    
    db_token_request.status = db_status
    db_token_request.response_date = datetime.now()
    db_token_request.approved_by_id = current_user.id
    
    db.commit()
    db.refresh(db_token_request)
    
    # If approved, create a token transaction
    if db_token_request.status == TokenRequestStatus.APPROVED:
        db_token = DBToken(
            user_id=db_token_request.user_id,
            amount=db_token_request.amount,
            transaction_type=TokenTransactionType.ADMIN_ADJUSTMENT,
            description=f"Approved token request #{db_token_request.id}",
            request_id=db_token_request.id
        )
        db.add(db_token)
        db.commit()
    
    # Send notification to the user about their token request status
    await NotificationManager.notify_token_request_status(
        db=db,
        request_id=request_id,
        user_id=db_token_request.user_id,
        approved=(db_token_request.status == TokenRequestStatus.APPROVED),
        admin_id=current_user.id,
        amount=db_token_request.amount
    )
    
    return convert_token_request_to_schema(db_token_request)

# Token routes
@router.get("/tokens/balance", response_model=UserTokenBalance)
def get_token_balance(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Calculate token balance by summing all transactions
    total_earned = db.query(func.coalesce(func.sum(DBToken.amount), 0)).filter(
        DBToken.user_id == current_user.id,
        DBToken.transaction_type.in_([TokenTransactionType.EARN, TokenTransactionType.ADMIN_ADJUSTMENT])
    ).scalar() or 0
    
    total_spent = db.query(func.coalesce(func.sum(DBToken.amount), 0)).filter(
        DBToken.user_id == current_user.id,
        DBToken.transaction_type == TokenTransactionType.SPEND
    ).scalar() or 0
    
    balance = total_earned - total_spent
    
    return UserTokenBalance(user_id=current_user.id, balance=balance)

@router.post("/tokens/spend", response_model=Token)
def spend_tokens(
    token: TokenCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Check if user has enough tokens
    balance = get_token_balance(db, current_user).balance
    if balance < token.amount:
        raise HTTPException(status_code=400, detail="Not enough tokens")
    
    # Create a spend transaction
    db_token = DBToken(
        user_id=current_user.id,
        amount=token.amount,
        transaction_type=TokenTransactionType.SPEND,
        description=token.description,
        request_id=token.request_id,
        workout_history_id=token.workout_history_id
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    return convert_token_to_schema(db_token)

@router.get("/tokens/history", response_model=List[Token])
def get_token_history(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    tokens = db.query(DBToken).filter(
        DBToken.user_id == current_user.id
    ).order_by(DBToken.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [convert_token_to_schema(token) for token in tokens]

@router.get("/admin/tokens/history", response_model=List[Token])
def get_all_users_token_history(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    query = db.query(DBToken)
    if user_id:
        query = query.filter(DBToken.user_id == user_id)
    
    tokens = query.order_by(DBToken.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [convert_token_to_schema(token) for token in tokens]

@router.get("/admin/tokens/requests", response_model=List[TokenRequest])
def get_all_token_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TokenRequestStatus] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    query = db.query(DBTokenRequest)
    if status:
        query = query.filter(DBTokenRequest.status == status)
    
    token_requests = query.order_by(DBTokenRequest.request_date.desc()).offset(skip).limit(limit).all()
    return [convert_token_request_to_schema(req) for req in token_requests]

@router.get("/admin/users/token-balance", response_model=List[UserTokenBalance])
def get_all_users_token_balance(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_admin_user)
):
    # Get all users
    users = db.query(DBUser).all()
    balances = []
    
    for user in users:
        # Calculate token balance by summing all transactions
        total_earned = db.query(func.coalesce(func.sum(DBToken.amount), 0)).filter(
            DBToken.user_id == user.id,
            DBToken.transaction_type.in_([TokenTransactionType.EARN, TokenTransactionType.ADMIN_ADJUSTMENT])
        ).scalar() or 0
        
        total_spent = db.query(func.coalesce(func.sum(DBToken.amount), 0)).filter(
            DBToken.user_id == user.id,
            DBToken.transaction_type == TokenTransactionType.SPEND
        ).scalar() or 0
        
        balance = total_earned - total_spent
        balances.append(UserTokenBalance(user_id=user.id, balance=balance))
    
    return balances

# S3 upload endpoint for profile image
@router.post("/users/profile/upload-image/", response_model=dict)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: DBUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg"]
        if file.content_type not in allowed_types:
            return {"success": False, "message": "Only JPEG and PNG images are allowed", "url": ""}
        
        # Create a unique filename
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        new_filename = f"profile_{current_user.id}_{uuid4()}.{file_extension}"
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3
        bucket_name = os.getenv("S3_BUCKET")
        s3_path = f"profile-images/{new_filename}"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_path,
            Body=file_content,
            ContentType=file.content_type
        )
        
        # Generate the URL
        s3_url = f"https://{bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_path}"
        
        # Update user profile with new image URL
        db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == current_user.id).first()
        
        if db_profile:
            db_profile.profile_image_url = s3_url
            db_profile.updated_at = datetime.now()
        else:
            # Create a profile if it doesn't exist
            db_profile = DBUserProfile(
                user_id=current_user.id,
                profile_image_url=s3_url
            )
            db.add(db_profile)
        
        db.commit()
        db.refresh(db_profile)
        
        return {
            "success": True,
            "message": "Profile image uploaded successfully to S3",
            "url": s3_url
        }
    except Exception as e:
        print(f"Error in upload_profile_image: {str(e)}")
        return {
            "success": False,
            "message": f"Error uploading image: {str(e)}",
            "url": ""
        }

# Notification routes
@router.get("/notifications/", response_model=List[Notification])
async def get_user_notifications(
    skip: int = 0,
    limit: int = 100,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Get a user's notifications
    """
    notifications = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only
    )
    
    return notifications

@router.get("/notifications/unread-count", response_model=Dict[str, int])
async def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Get the count of unread notifications for the current user
    """
    count = NotificationService.get_unread_count(db=db, user_id=current_user.id)
    return {"count": count}

@router.put("/notifications/{notification_id}/read", response_model=Notification)
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Mark a notification as read
    """
    notification = NotificationService.mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    
    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )
    
    return notification

@router.put("/notifications/read-all", response_model=Dict[str, int])
async def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Mark all notifications for the current user as read
    """
    count = NotificationService.mark_all_notifications_as_read(db=db, user_id=current_user.id)
    return {"count": count}

@router.delete("/notifications/{notification_id}", response_model=Dict[str, bool])
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Delete a notification
    """
    success = NotificationService.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )
    
    return {"success": True}
    
# Testing notification endpoint (for development)
@router.post("/test-notification", response_model=Dict[str, str])
async def send_test_notification(
    message: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    """
    Send a test notification to the current user
    """
    await NotificationManager.create_and_send_notification(
        db=db,
        notification_type=DBNotificationType.SYSTEM_NOTIFICATION,
        user_id=current_user.id,
        title="Test Notification",
        message=message,
        data={"test": True}
    )
    
    return {"status": "notification sent"}

# Scheduled Workout routes
@router.post("/scheduled-workouts/", response_model=ScheduledWorkout)
async def schedule_workout(
    scheduled_workout: ScheduledWorkoutCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Check if workout template exists
    workout_template = db.query(DBWorkout).filter(DBWorkout.id == scheduled_workout.workout_template_id).first()
    if not workout_template:
        raise HTTPException(status_code=404, detail="Workout template not found")
    
    # Calculate end time
    scheduled_end_time = scheduled_workout.scheduled_date + timedelta(minutes=scheduled_workout.duration_minutes)
    
    # Check for scheduling conflicts using Python logic
    # Get all non-completed scheduled workouts for this user
    existing_workouts = db.query(DBScheduledWorkout).filter(
        DBScheduledWorkout.user_id == current_user.id,
        DBScheduledWorkout.is_completed == False
    ).all()
    
    # Check each workout for conflicts
    conflicting_workout = None
    for workout in existing_workouts:
        existing_end_time = workout.scheduled_date + timedelta(minutes=workout.duration_minutes)
        
        # Ensure consistent timezone awareness for comparison
        scheduled_workout_date = scheduled_workout.scheduled_date
        scheduled_end_time = scheduled_workout_date + timedelta(minutes=scheduled_workout.duration_minutes)
        
        # Check if one datetime has tzinfo and the other doesn't, make them both naive
        if (workout.scheduled_date.tzinfo is None) != (scheduled_workout_date.tzinfo is None):
            # Convert to naive datetime if needed
            if workout.scheduled_date.tzinfo is not None:
                workout_start = workout.scheduled_date.replace(tzinfo=None)
                workout_end = existing_end_time.replace(tzinfo=None)
            else:
                workout_start = workout.scheduled_date
                workout_end = existing_end_time
                
            if scheduled_workout_date.tzinfo is not None:
                scheduled_start = scheduled_workout_date.replace(tzinfo=None)
                scheduled_end = scheduled_end_time.replace(tzinfo=None)
            else:
                scheduled_start = scheduled_workout_date
                scheduled_end = scheduled_end_time
        else:
            # Both datetimes have the same tzinfo state
            workout_start = workout.scheduled_date
            workout_end = existing_end_time
            scheduled_start = scheduled_workout_date
            scheduled_end = scheduled_end_time
        
        # Check for overlap
        if (
            # Case 1: New workout starts during an existing workout
            (workout_start <= scheduled_start <= workout_end) or
            # Case 2: New workout ends during an existing workout
            (workout_start <= scheduled_end <= workout_end) or
            # Case 3: New workout completely contains an existing workout
            (scheduled_start <= workout_start and scheduled_end >= workout_end)
        ):
            conflicting_workout = workout
            break
    
    if conflicting_workout:
        raise HTTPException(
            status_code=400, 
            detail="Scheduling conflict: You already have a workout scheduled during this time"
        )
    
    # Create a copy of the workout template as a scheduled workout
    db_scheduled_workout = DBScheduledWorkout(
        user_id=current_user.id,
        workout_template_id=scheduled_workout.workout_template_id,
        title=scheduled_workout.title,
        description=scheduled_workout.description,
        scheduled_date=scheduled_workout.scheduled_date,
        duration_minutes=scheduled_workout.duration_minutes,
        is_completed=False
    )
    db.add(db_scheduled_workout)
    db.commit()
    db.refresh(db_scheduled_workout)
    
    # Get exercises from the template workout if not provided in the request
    if not scheduled_workout.exercises:
        template_exercises = db.query(DBWorkoutExercise).filter(
            DBWorkoutExercise.workout_id == scheduled_workout.workout_template_id
        ).all()
        
        for exercise in template_exercises:
            db_scheduled_exercise = DBScheduledWorkoutExercise(
                scheduled_workout_id=db_scheduled_workout.id,
                exercise_id=exercise.exercise_id,
                sets=exercise.sets,
                reps=exercise.reps,
                weight=exercise.weight,
                notes=exercise.notes
            )
            db.add(db_scheduled_exercise)
    else:
        # Add exercises from request if provided
        for exercise_data in scheduled_workout.exercises:
            db_scheduled_exercise = DBScheduledWorkoutExercise(
                scheduled_workout_id=db_scheduled_workout.id,
                **exercise_data.dict()
            )
            db.add(db_scheduled_exercise)
    
    db.commit()
    db.refresh(db_scheduled_workout)
    return db_scheduled_workout

@router.get("/scheduled-workouts/", response_model=List[ScheduledWorkout])
def get_scheduled_workouts(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_completed: bool = False,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    query = db.query(DBScheduledWorkout).filter(DBScheduledWorkout.user_id == current_user.id)
    
    if not include_completed:
        query = query.filter(DBScheduledWorkout.is_completed == False)
    
    if start_date:
        query = query.filter(DBScheduledWorkout.scheduled_date >= start_date)
    if end_date:
        query = query.filter(DBScheduledWorkout.scheduled_date <= end_date)
    
    scheduled_workouts = query.order_by(DBScheduledWorkout.scheduled_date).offset(skip).limit(limit).all()
    return scheduled_workouts

@router.get("/scheduled-workouts/{scheduled_workout_id}", response_model=ScheduledWorkout)
def get_scheduled_workout(
    scheduled_workout_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    scheduled_workout = db.query(DBScheduledWorkout).filter(
        DBScheduledWorkout.id == scheduled_workout_id,
        DBScheduledWorkout.user_id == current_user.id
    ).first()
    
    if scheduled_workout is None:
        raise HTTPException(status_code=404, detail="Scheduled workout not found")
    
    return scheduled_workout

@router.post("/scheduled-workouts/{scheduled_workout_id}/start", response_model=WorkoutHistory)
async def start_scheduled_workout(
    scheduled_workout_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    # Get the scheduled workout
    scheduled_workout = db.query(DBScheduledWorkout).filter(
        DBScheduledWorkout.id == scheduled_workout_id,
        DBScheduledWorkout.user_id == current_user.id
    ).first()
    
    if scheduled_workout is None:
        raise HTTPException(status_code=404, detail="Scheduled workout not found")
    
    if scheduled_workout.is_completed:
        raise HTTPException(status_code=400, detail="This scheduled workout has already been completed")
    
    # Create a workout history entry from the scheduled workout
    db_workout_history = DBWorkoutHistory(
        user_id=current_user.id,
        workout_template_id=scheduled_workout.workout_template_id,
        title=scheduled_workout.title,
        duration_minutes=scheduled_workout.duration_minutes,
        notes=f"Started from scheduled workout on {scheduled_workout.scheduled_date}"
    )
    db.add(db_workout_history)
    db.commit()
    db.refresh(db_workout_history)
    
    # Get the exercises from the scheduled workout
    scheduled_exercises = db.query(DBScheduledWorkoutExercise).filter(
        DBScheduledWorkoutExercise.scheduled_workout_id == scheduled_workout_id
    ).all()
    
    # Add exercises to workout history
    for exercise in scheduled_exercises:
        db_workout_history_exercise = DBWorkoutHistoryExercise(
            workout_history_id=db_workout_history.id,
            exercise_id=exercise.exercise_id,
            sets=exercise.sets,
            reps=exercise.reps,
            weight=exercise.weight,
            notes=exercise.notes
        )
        db.add(db_workout_history_exercise)
    
    # Mark the scheduled workout as completed
    scheduled_workout.is_completed = True
    db.commit()
    db.refresh(db_workout_history)
    
    # Award tokens for completing a workout
    token_amount = 10  # Default amount for completing a workout
    
    db_token = DBToken(
        user_id=current_user.id,
        amount=token_amount,
        transaction_type=TokenTransactionType.EARN,
        description=f"Completed scheduled workout: {scheduled_workout.title}",
        workout_history_id=db_workout_history.id
    )
    db.add(db_token)
    db.commit()
    
    # Send notification about completed workout and tokens earned
    await NotificationManager.notify_workout_completed(
        db=db,
        user_id=current_user.id,
        workout_history_id=db_workout_history.id,
        title=scheduled_workout.title,
        tokens_earned=token_amount
    )
    
    return db_workout_history

@router.delete("/scheduled-workouts/{scheduled_workout_id}", status_code=204)
def delete_scheduled_workout(
    scheduled_workout_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_active_user)
):
    scheduled_workout = db.query(DBScheduledWorkout).filter(
        DBScheduledWorkout.id == scheduled_workout_id,
        DBScheduledWorkout.user_id == current_user.id
    ).first()
    
    if scheduled_workout is None:
        raise HTTPException(status_code=404, detail="Scheduled workout not found")
    
    db.delete(scheduled_workout)
    db.commit()
    return 
