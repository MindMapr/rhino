# app/controllers/feedback_controller.py

from uuid import UUID
from fastapi import HTTPException, status
from typing import List, Union
from ..models.feedback import (
    ContextSpecificFeedback,
    FeedbackCategory,
    PromptFeedback,
    Feedback,
)

conflict = "Prompt already shown"

class FeedbackList:
    def __init__(self, db):
        self.db = db
    
    # Create a new prompt feedback
    def create_prompt(self, prompt_feedback: PromptFeedback) -> PromptFeedback:
        # existing = self.db.find_one({
        #     "user_id": prompt_feedback.user_id,
        #     "prompt": prompt_feedback.prompt
        # })
        # if existing:
        #     raise HTTPException(
        #         status_code=status.HTTP_409_CONFLICT,
        #         detail=conflict
        #     )
        document = prompt_feedback.model_dump(by_alias=True, exclude_none=True)
        self.db.insert_one(document)
        return prompt_feedback

    # Create new standard feedback
    def create_feedback(self, feedback: Feedback) -> Feedback:
        document = feedback.model_dump(by_alias=True, exclude_none=True)
        self.db.insert_one(document)
        return feedback
    
    def get_categories(self) -> List[str]:
        return [category.value for category in FeedbackCategory]
    
    def get_prompts(self) -> List[str]:
        return [prompt.value for prompt in ContextSpecificFeedback]
    
    # Useful for us if we want to find all feedback from one specific user
    def list_by_user(self, user_id: str) -> List[Union[Feedback, PromptFeedback]]:
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format"
            )
        documents = list(self.db.find({"user_id": user_uuid}))
        result: List[Union[Feedback, PromptFeedback]] = []
        for document in documents:
            if "prompt" == document.get("feedback_type"):
                result.append(PromptFeedback(**document))
            else:
                result.append(Feedback(**document))
        return result
