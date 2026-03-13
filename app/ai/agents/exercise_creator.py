import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.models import AIAgentType, Exercise
from app.ai.base_agent import BaseAgent

class ExerciseCreatorAgent(BaseAgent):
    """Agent that creates new exercise recommendations based on existing exercises"""
    
    def __init__(self, db: Session, user_id: int = None):
        super().__init__(db, AIAgentType.EXERCISE_CREATOR, user_id)
    
    def _get_exercises_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Fetch exercises from the database by category"""
        exercises = self.db.query(Exercise).filter(Exercise.category == category).all()
        
        return [
            {
                "id": exercise.id,
                "name": exercise.name,
                "description": exercise.description,
                "muscle_groups": exercise.muscle_groups,
                "difficulty": exercise.difficulty,
                "equipment": exercise.equipment
            }
            for exercise in exercises
        ]
    
    def prepare_prompt(self, input_data: Dict[str, Any]) -> str:
        """Prepare prompt for exercise creation"""
        category = input_data.get("category")
        if not category:
            raise ValueError("Category is required to create new exercises")
        
        # Get existing exercises in this category
        existing_exercises = self._get_exercises_by_category(category)
        
        # Format the existing exercises as a string
        existing_exercises_text = "\n".join([
            f"{i+1}. {ex['name']} - {ex['description'] or 'No description'}"
            for i, ex in enumerate(existing_exercises)
        ])
        
        # Create the prompt
        prompt = f"""
        I need your help to create new exercise recommendations for the '{category}' category.
        
        Here are the existing exercises in this category:
        
        {existing_exercises_text}
        
        Please suggest 5 new exercises for the '{category}' category that are not in the list above.
        For each exercise, provide:
        
        1. Exercise name
        2. Description
        3. Primary muscle groups worked
        4. Difficulty level (Beginner, Intermediate, Advanced)
        5. Required equipment (if any)
        6. Brief instructions on how to perform the exercise
        
        Format your response as a JSON array with objects containing these fields:
        name, description, muscle_groups, difficulty, equipment, instructions
        
        Example format:
        ```json
        [
            {{
                "name": "Exercise Name",
                "description": "Brief description",
                "muscle_groups": "Primary muscles worked",
                "difficulty": "Beginner/Intermediate/Advanced",
                "equipment": "Required equipment or 'None' if bodyweight",
                "instructions": "Step-by-step instructions"
            }}
        ]
        ```
        
        Only include the JSON in your response, no other text.
        """
        
        return prompt
    
    def process_response(self, response: str) -> Dict[str, Any]:
        """Process the AI response, extracting the JSON data"""
        try:
            # Try to extract JSON from the response if it's wrapped in code blocks
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_text = response.split("```")[1].strip()
            else:
                json_text = response.strip()
            
            # Parse the JSON
            exercises = json.loads(json_text)
            
            # Validate the structure
            for exercise in exercises:
                required_fields = ["name", "description", "muscle_groups", "difficulty", "equipment", "instructions"]
                for field in required_fields:
                    if field not in exercise:
                        exercise[field] = "Not provided"
            
            return {
                "exercises": exercises,
                "count": len(exercises)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse exercise data from AI response: {str(e)}") 