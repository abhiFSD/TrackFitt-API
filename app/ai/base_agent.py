import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import AITracking, AIAgentType, AITrackingStatus
from app.db.database import get_db

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, db: Session, agent_type: AIAgentType, user_id: Optional[int] = None):
        self.db = db
        self.agent_type = agent_type
        self.user_id = user_id
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
        
    @abstractmethod
    def prepare_prompt(self, input_data: Dict[str, Any]) -> str:
        """Prepare the prompt to be sent to the AI model"""
        pass
        
    @abstractmethod
    def process_response(self, response: str) -> Dict[str, Any]:
        """Process the response from the AI model"""
        pass
        
    async def call_ai_api(self, prompt: str) -> str:
        """Call the DeepSeek API and return the response"""
        import aiohttp
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant specialized in fitness and exercise."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"API call failed with status {response.status}: {error_text}")
    
    def create_tracking_entry(self, prompt: str, input_data: Dict[str, Any]) -> AITracking:
        """Create a new AI tracking entry in the database"""
        tracking_entry = AITracking(
            user_id=self.user_id,
            agent_type=self.agent_type,
            prompt=prompt,
            input_data=json.dumps(input_data),
            status=AITrackingStatus.INITIATED
        )
        
        self.db.add(tracking_entry)
        self.db.commit()
        self.db.refresh(tracking_entry)
        return tracking_entry
        
    def update_tracking_entry(self, tracking_entry: AITracking, response: str, 
                              output_data: Dict[str, Any], status: AITrackingStatus) -> AITracking:
        """Update an existing AI tracking entry in the database"""
        tracking_entry.response = response
        tracking_entry.output_data = json.dumps(output_data)
        tracking_entry.status = status
        tracking_entry.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(tracking_entry)
        return tracking_entry
        
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent workflow: prepare prompt, call API, process response, and track in DB"""
        try:
            # Prepare the prompt
            prompt = self.prepare_prompt(input_data)
            
            # Create tracking entry
            tracking_entry = self.create_tracking_entry(prompt, input_data)
            
            # Call the API
            response = await self.call_ai_api(prompt)
            
            # Process the response
            output_data = self.process_response(response)
            
            # Update tracking entry
            self.update_tracking_entry(
                tracking_entry=tracking_entry,
                response=response,
                output_data=output_data,
                status=AITrackingStatus.COMPLETED
            )
            
            return {
                "success": True,
                "tracking_id": tracking_entry.id,
                "data": output_data
            }
            
        except Exception as e:
            # Update tracking entry with error
            if 'tracking_entry' in locals():
                self.update_tracking_entry(
                    tracking_entry=tracking_entry,
                    response=str(e),
                    output_data={"error": str(e)},
                    status=AITrackingStatus.FAILED
                )
            
            return {
                "success": False,
                "error": str(e),
                "tracking_id": tracking_entry.id if 'tracking_entry' in locals() else None
            } 