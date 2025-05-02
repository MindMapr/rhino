from typing import Annotated, List, Union
from fastapi import APIRouter, Depends
from ..database.mongodb import database
from app.controllers.feedback import FeedbackList
from app.models.feedback import CreateFeedback, CreatePromptFeedback, Feedback, PromptFeedback
from app.utils.auth import get_current_user

# Setup collection
collection = database.feedback

# Router
router = APIRouter(prefix="/feedback", tags=["feedback"])

# Controllers
list_routes = FeedbackList(collection)

# Dependencies
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.post("/prompt", response_model=PromptFeedback, status_code=201)
def create_prompt(params: CreatePromptFeedback, current_user: user_dependency):
    prompt_feedback = PromptFeedback(
        user_id=current_user["_id"],
        prompt=params.prompt,
        feedback=params.feedback
    )
    return list_routes.create_prompt(prompt_feedback)


@router.post("/feedback", response_model=Feedback, status_code=201)
def create_feedback(params: CreateFeedback, current_user: user_dependency):
    feedback = Feedback(
        user_id=current_user["_id"],
        feedback_category=params.feedback_category,
        context=params.context,
        feedback=params.feedback
    )
    return list_routes.create_feedback(feedback)


@router.get("/user", response_model=List[Union[Feedback, PromptFeedback]])
def get_by_user(current_user: user_dependency):
    return list_routes.list_by_user(current_user["_id"])