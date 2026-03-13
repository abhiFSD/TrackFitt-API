import json
import time
import requests
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.models.models import AITracking, AIOperationType, Exercise
from app.schemas.ai_schemas import WorkoutAIRequest, WorkoutAIResponse, AITrackingCreate
import os
from dotenv import load_dotenv

load_dotenv()

# Get API keys and URLs from environment variables
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Commented out or removed
# OPENAI_API_URL = "https://api.openai.com/v1/chat/completions" # Commented out or removed
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions") # Default if not set

logger = logging.getLogger(__name__)

class AIService:
    # Update __init__ to use DeepSeek credentials
    def __init__(self, api_key: str = DEEPSEEK_API_KEY, api_url: str = DEEPSEEK_API_URL):
        self.api_key = api_key
        self.api_url = api_url
        if not self.api_key:
            logger.warning("DeepSeek API key not provided. AI features will not work.")
        if not self.api_url:
            logger.warning("DeepSeek API URL not provided. AI features will not work.")

    def track_operation(self, db: Session, operation_type: AIOperationType, 
                        user_id: int, prompt: str, input_data: Dict = None,
                        response_data: Dict = None, duration_ms: int = None,
                        metadata: Dict = None, status: str = "completed") -> AITracking:
        """Track an AI operation in the database"""
        ai_tracking = AITracking(
            user_id=user_id,
            operation_type=operation_type,
            user_prompt=prompt,
            input_data=json.dumps(input_data) if input_data else None,
            response_data=json.dumps(response_data) if response_data else None,
            status=status,
            duration_ms=duration_ms,
            metadata=json.dumps(metadata) if metadata else None
        )
        
        db.add(ai_tracking)
        db.commit()
        db.refresh(ai_tracking)
        return ai_tracking

    def create_workout(self, db: Session, request: WorkoutAIRequest) -> WorkoutAIResponse:
        """Create a workout using AI based on user input and available exercises"""
        start_time = time.time()
        
        available_exercises_list = request.available_exercises
        if not available_exercises_list:
            exercises = db.query(Exercise).all()
            available_exercises_list = [
                {
                    "id": exercise.id,
                    "name": exercise.name,
                    "category": exercise.category,
                    "muscle_groups": exercise.muscle_groups,
                    "equipment": exercise.equipment
                } for exercise in exercises
            ]
        
        # Format the input for the AI, including the new shared profile data
        input_data = {
            "user_prompt": request.user_prompt,
            "fitness_level": request.fitness_level,
            "preferred_duration": request.preferred_duration,
            "preferred_equipment": request.preferred_equipment,
            "target_muscle_groups": request.target_muscle_groups,
            "available_exercises": available_exercises_list, # Use the list directly
            "shared_profile_data": request.shared_profile_data # Include the shared data
        }
        
        try:
            response = self._call_deepseek_api(input_data)
            workout_response = self._parse_deepseek_response(response)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Prepare input_data for tracking (remove potentially large available_exercises)
            tracking_input = input_data.copy()
            if len(tracking_input.get("available_exercises", [])) > 20: # Only log summary if many exercises
                tracking_input["available_exercises_summary"] = f"{len(tracking_input.pop('available_exercises', []))} exercises provided"
            else:
                tracking_input["available_exercises"] = json.dumps(tracking_input.get("available_exercises"))
            
            self.track_operation(
                db=db,
                operation_type=AIOperationType.WORKOUT_CREATION,
                user_id=request.user_id,
                prompt=request.user_prompt,
                input_data=tracking_input, # Log modified input data
                response_data=workout_response.dict(),
                duration_ms=duration_ms
            )
            return workout_response
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            # Prepare input_data for tracking on failure
            tracking_input = input_data.copy()
            if len(tracking_input.get("available_exercises", [])) > 20:
                tracking_input["available_exercises_summary"] = f"{len(tracking_input.pop('available_exercises', []))} exercises provided"
            else:
                tracking_input["available_exercises"] = json.dumps(tracking_input.get("available_exercises"))

            self.track_operation(
                db=db,
                operation_type=AIOperationType.WORKOUT_CREATION,
                user_id=request.user_id,
                prompt=request.user_prompt,
                input_data=tracking_input, # Log modified input data
                status="failed",
                metadata={"error": str(e)},
                duration_ms=duration_ms
            )
            logger.error(f"Error in create_workout: {e}")
            raise

    def _format_profile_data_for_prompt(self, profile_data: Optional[Dict[str, Any]]) -> str:
        """Formats the selected user profile data into a string for the AI prompt."""
        if not profile_data:
            return ""
        
        prompt_parts = []
        
        if "basicInfo" in profile_data and profile_data["basicInfo"]:
            basic_info = profile_data["basicInfo"]
            info_str = "Basic Info:"
            if basic_info.get("age") is not None:
                info_str += f" Age {basic_info['age']}"
            if basic_info.get("gender"):
                info_str += f" Gender {basic_info['gender']}"
            if info_str != "Basic Info:": prompt_parts.append(info_str)

        if "physicalMetrics" in profile_data and profile_data["physicalMetrics"]:
            metrics = profile_data["physicalMetrics"]
            metrics_str = "Physical Metrics:"
            if metrics.get("height_cm") is not None:
                metrics_str += f" Height {metrics['height_cm']}cm"
            if metrics.get("weight_kg") is not None:
                metrics_str += f" Weight {metrics['weight_kg']}kg"
            if metrics.get("body_fat_percentage") is not None:
                metrics_str += f" Body Fat {metrics['body_fat_percentage']}%"
            if metrics_str != "Physical Metrics:": prompt_parts.append(metrics_str)

        if "fitnessActivity" in profile_data and profile_data["fitnessActivity"]:
            fitness = profile_data["fitnessActivity"]
            fitness_str = "Fitness/Activity:"
            if fitness.get("activity_level"):
                fitness_str += f" Activity Level {fitness['activity_level']}"
            if fitness.get("weekly_workout_goal") is not None:
                 fitness_str += f" Weekly Goal {fitness['weekly_workout_goal']} workouts"
            if fitness_str != "Fitness/Activity:": prompt_parts.append(fitness_str)
            
        if "healthInfo" in profile_data and profile_data["healthInfo"]:
            health = profile_data["healthInfo"]
            health_str = "Health Info:"
            if health.get("has_injuries"):
                 health_str += f" Injuries/Limitations: {health.get('injury_notes', 'Yes, details not provided')}"
            if health.get("has_medical_conditions"):
                 health_str += f" Medical Conditions: {health.get('medical_notes', 'Yes, details not provided')}"
            if health_str != "Health Info:": prompt_parts.append(health_str)
            
        if "goals" in profile_data and profile_data["goals"]:
            goals = profile_data["goals"]
            goals_str = "Goals:"
            if goals.get("weight_goal_kg") is not None:
                 goals_str += f" Target Weight {goals['weight_goal_kg']}kg"
            if goals_str != "Goals:": prompt_parts.append(goals_str)
            
        if "preferences" in profile_data and profile_data["preferences"]:
            prefs = profile_data["preferences"]
            prefs_str = "Preferences:"
            if prefs.get("preferred_workout_days"):
                 prefs_str += f" Prefers workout on: {', '.join(prefs['preferred_workout_days'])}"
            if prefs.get("favorite_muscle_groups"):
                 prefs_str += f" Enjoys training: {', '.join(prefs['favorite_muscle_groups'])}"
            if prefs_str != "Preferences:": prompt_parts.append(prefs_str)

        if prompt_parts:
            return "\n\nUser Profile Context:\n" + "\n".join(prompt_parts)
        else:
            return ""

    def _call_deepseek_api(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call DeepSeek API with the workout creation prompt, including optional profile data"""
        if not self.api_key or not self.api_url:
             logger.error("DeepSeek API Key or URL is not configured.")
             raise ValueError("AI Service is not configured.")
        
        exercises_data = ""
        for idx, exercise in enumerate(input_data.get("available_exercises", [])):
             # Ensure exercise is a dict before accessing keys
            if isinstance(exercise, dict):
                exercise_id = exercise.get('id', 'N/A') # Default to 'N/A' if id is missing
                exercise_name = exercise.get('name', 'Unnamed Exercise')
                exercises_data += f"{idx+1}. Name: {exercise_name} (Database ID: {exercise_id})"
                if exercise.get("category"):
                    exercises_data += f", Category: {exercise['category']}"
                if exercise.get("muscle_groups"):
                    exercises_data += f", Muscles: {exercise['muscle_groups']}"
                if exercise.get("equipment"):
                    exercises_data += f", Equipment: {exercise['equipment']}"
                exercises_data += "\n"
            else:
                logger.warning(f"Skipping malformed exercise data in prompt: {exercise}")

        
        # Format profile data
        profile_context = self._format_profile_data_for_prompt(input_data.get("shared_profile_data"))

        # Build the prompts
        system_prompt = f"""
        You are a professional fitness trainer AI. Your task is to create a workout plan based on the user's requirements and provided profile context.
        Generate a complete workout plan with exercises, sets, reps, and rest times.
        IMPORTANT: You MUST only use exercises from the provided list. For each exercise in your response,
        you MUST use the **integer** `Database ID` provided in the list for the `exercise_id` field in your JSON output.
        Consider the user's profile information ({'provided' if profile_context else 'not provided'}) to tailor the workout.
        Format your response as a valid JSON object with the following structure:
        {{
            "title": "Workout title",
            "description": "Brief description of the workout",
            "duration_minutes": estimated_duration_in_minutes,
            "difficulty_level": "beginner/intermediate/advanced",
            "exercises": [
                {{
                    "exercise_id": integer_database_id_from_list,
                    "sets": number_of_sets,
                    "reps": number_of_reps_per_set,
                    "weight": optional_suggested_weight_or_null,
                    "rest_time_seconds": rest_time_between_sets,
                    "notes": "Optional notes for this exercise"
                }}
            ],
            "ai_notes": "Additional notes or tips about the workout, potentially referencing used profile data"
        }}
        DO NOT include ANY explanation outside the JSON. Return ONLY valid JSON.
        """
        
        user_prompt_content = f"""
        User workout request: {input_data.get('user_prompt', '')}
        
        User fitness level: {input_data.get('fitness_level', 'Not specified')}
        Preferred duration: {input_data.get('preferred_duration', 'Not specified')} minutes
        Preferred equipment: {', '.join(input_data.get('preferred_equipment', [])) if input_data.get('preferred_equipment') else 'Not specified'}
        Target muscle groups: {', '.join(input_data.get('target_muscle_groups', [])) if input_data.get('target_muscle_groups') else 'Not specified'}
        {profile_context} 
        Available exercises (Use the integer 'Database ID' for the 'exercise_id' in your response):
        {exercises_data if exercises_data else 'No specific exercises provided, choose suitable ones.'}
        
        Create a workout that matches these requirements. Remember to ONLY use exercises from the list above (if provided) and use their integer Database ID.
        Tailor the plan based on the provided user profile context if available.
        """
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        logger.debug(f"Sending payload to DeepSeek: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60 # Add a timeout
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            raise ValueError(f"Failed to connect to AI service: {e}")
        except Exception as e:
             logger.error(f"Unexpected error during DeepSeek API call: {e}")
             raise

    def _parse_deepseek_response(self, deepseek_response: Dict[str, Any]) -> WorkoutAIResponse:
        """Parse the DeepSeek API response into a WorkoutAIResponse"""
        try:
            # Extract the content from the DeepSeek response (assuming same structure as OpenAI)
            content = deepseek_response["choices"][0]["message"]["content"]
            logger.info(f"Raw content from DeepSeek: {content[:500]}...") # Log truncated content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("{") and content.endswith("}"):
                # Assume it's already JSON if it starts/ends with braces
                content = content.strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            else:
                 # If no markdown, attempt to parse directly, but log warning
                 logger.warning("AI response did not contain markdown JSON block. Attempting direct parse.")
                 content = content.strip()

            workout_data = json.loads(content)
            logger.info(f"Parsed workout_data from AI: {workout_data}")
            
            for ex in workout_data.get('exercises', []):
                if 'exercise_id' not in ex:
                    logger.error(f"AI response missing 'exercise_id' in exercise: {ex}")
                    raise ValueError("AI response missing 'exercise_id' in one or more exercises.")
                
                if not isinstance(ex['exercise_id'], int):
                    try:
                        # Attempt conversion if it looks like an int
                        ex['exercise_id'] = int(ex['exercise_id'])
                        logger.warning(f"Converted non-integer exercise_id '{ex['exercise_id']}' to int.")
                    except (ValueError, TypeError):
                         logger.error(f"AI returned non-integer exercise_id that could not be converted: {ex['exercise_id']} (Type: {type(ex['exercise_id'])})")
                         raise ValueError(f"AI returned non-integer exercise_id: {ex['exercise_id']}")
                logger.debug(f"Validated exercise_id: {ex.get('exercise_id')}")

            return WorkoutAIResponse(**workout_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from DeepSeek response: {e}")
            logger.error(f"Response content that failed parsing: {content}") 
            raise ValueError(f"AI returned invalid JSON: {e}")
        except (KeyError, IndexError, TypeError) as e:
             logger.error(f"Error accessing expected structure in DeepSeek response: {e}")
             logger.error(f"Response structure: {deepseek_response}")
             raise ValueError(f"AI response structure was unexpected: {e}")
        except Exception as e:
            logger.error(f"Error parsing DeepSeek response: {e}")
            logger.error(f"Response structure causing parse error: {deepseek_response}")
            raise ValueError(f"Failed to parse DeepSeek response: {e}")

# Instantiation uses the updated __init__ defaults
ai_service = AIService() 