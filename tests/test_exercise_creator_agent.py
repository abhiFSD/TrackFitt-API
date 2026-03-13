import pytest
import json
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock

from app.models.models import Exercise, AIAgentType, AITrackingStatus
from app.ai.agents import ExerciseCreatorAgent

@pytest.fixture
def mock_exercise_data():
    return [
        {
            "id": 1,
            "name": "Test Exercise 1", 
            "description": "Test Description 1",
            "category": "strength",
            "muscle_groups": "chest, shoulders",
            "difficulty": "intermediate",
            "equipment": "dumbbells",
            "exercise_id": "ex123"
        },
        {
            "id": 2,
            "name": "Test Exercise 2",
            "description": "Test Description 2",
            "category": "strength",
            "muscle_groups": "back, biceps",
            "difficulty": "beginner",
            "equipment": "bodyweight",
            "exercise_id": "ex456"
        }
    ]

@pytest.fixture
def mock_ai_response():
    return """```json
[
    {
        "name": "Weighted Diamond Push-ups",
        "description": "An advanced variation of push-ups that targets the chest, triceps, and shoulders with added resistance.",
        "muscle_groups": "Chest, Triceps, Shoulders",
        "difficulty": "Advanced",
        "equipment": "Weight plate or weighted vest",
        "instructions": "1. Start in a standard push-up position with hands close together forming a diamond shape.\n2. Place a weight plate on your upper back or wear a weighted vest.\n3. Lower your chest to the ground while keeping elbows close to your body.\n4. Push back up to starting position.\n5. Repeat for desired reps."
    },
    {
        "name": "Incline Dumbbell Pullovers",
        "description": "A compound exercise that works the chest, lats, and serratus anterior muscles.",
        "muscle_groups": "Chest, Lats, Serratus Anterior",
        "difficulty": "Intermediate",
        "equipment": "Incline bench, Dumbbell",
        "instructions": "1. Lie on an incline bench with feet firmly on the ground.\n2. Hold a dumbbell with both hands extended above your chest.\n3. Keeping a slight bend in your elbows, lower the weight back over your head until you feel a stretch in your lats.\n4. Return to starting position by engaging your chest and lats.\n5. Repeat for desired reps."
    }
]```"""

@pytest.fixture
def mock_db_session(mock_exercise_data):
    with patch("sqlalchemy.orm.Session") as mock_session:
        mock_query = mock_session.return_value.query
        mock_filter = mock_query.return_value.filter
        mock_filter.return_value.all.return_value = [
            type('Exercise', (), exercise_data) for exercise_data in mock_exercise_data
        ]
        yield mock_session.return_value

@pytest.mark.asyncio
async def test_exercise_creator_agent(mock_db_session, mock_ai_response):
    # Arrange
    with patch.object(ExerciseCreatorAgent, "call_ai_api", new_callable=AsyncMock) as mock_call_api:
        mock_call_api.return_value = mock_ai_response
        
        mock_db_session.add = lambda x: None
        mock_db_session.commit = lambda: None
        mock_db_session.refresh = lambda x: None
        
        agent = ExerciseCreatorAgent(db=mock_db_session, user_id=1)
        
        # Act
        result = await agent.run({"category": "strength"})
        
        # Assert
        assert result["success"] is True
        assert "data" in result
        assert "exercises" in result["data"]
        assert len(result["data"]["exercises"]) == 2
        
        # Verify the prompt was prepared correctly
        prompt = agent.prepare_prompt({"category": "strength"})
        assert "strength" in prompt
        assert "existing exercises" in prompt
        
        # Verify API was called
        mock_call_api.assert_called_once()
        
        # Verify response was processed correctly
        processed_data = agent.process_response(mock_ai_response)
        assert len(processed_data["exercises"]) == 2
        assert processed_data["exercises"][0]["name"] == "Weighted Diamond Push-ups"
        assert processed_data["exercises"][1]["name"] == "Incline Dumbbell Pullovers" 