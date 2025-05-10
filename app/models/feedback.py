from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ContextSpecificFeedback(str, Enum):
    first_average_feedback = "first_average_feedback"
    completed_after_estimation_suggestion = "completed_after_estimation_suggestion"
    seen_calendar_first_time = "seen_calendar_first_time"
    
class FeedbackCategory(str, Enum):
    bug = "bug"
    feature_request = "feature_request"
    user_experience = "user_experience"
    other = "other"
# Since several fields are the same we have a base model for feedback and then add what we need to it as well
class BaseModelFeedback(BaseModel):
    feedback_id: UUID = Field(default_factory=uuid4, alias="_id")
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.now, description="Useful knowledge to know in case we do updates during the study")
    
    
class PromptFeedback(BaseModelFeedback):
    feedback_type: Literal["prompt"] = "prompt"
    prompt: ContextSpecificFeedback
    feedback: str = Field(..., description="The actual feedback from the user")
    #shown: bool = Field(default=False, description="Check so prompt feedback do not repeat")

class Feedback(BaseModelFeedback):
    feedback_type: Literal["feedback"] = "feedback"
    feedback: str = Field(..., description="The actual feedback from the user")
    context: str = Field(..., description="An input on what page the user is on when giving the feedback")
    feedback_category: FeedbackCategory = Field(..., description="Could be useful to have the user give input on what type of feedback it is")
    
    
class CreatePromptFeedback(BaseModel):
    prompt: ContextSpecificFeedback
    feedback: str
    
class CreateFeedback(BaseModel):
    feedback: str
    context: str
    feedback_category: FeedbackCategory