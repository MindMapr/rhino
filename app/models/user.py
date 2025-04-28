from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from app.models.task import TaskCategory
# from ..utils.parse_objectId import PydanticObjectId

class CategoryStats(BaseModel):
    history: List[float] = Field(
        default_factory=list,
        description="List of pct-error values for each completed task"
    )
    # average percent over/under estimate
    avg_pct_error: float = 0.0   

# User schema
class User(BaseModel):
    user_id: UUID = Field(default_factory=uuid4, alias="_id") 
    username: str
    email: EmailStr
    password: str
    created_at: datetime = Field(default_factory = lambda: datetime.now())
    estimation_average_for_category: Dict[str, CategoryStats] = Field(default_factory=lambda: {
            category: CategoryStats() for category in TaskCategory
        })
    # SUGGESTION: Maybe a personal enum for task they create, that we do not have?
    # TODO: add profile image?

    
    @field_validator('password', mode='after') 
    def check_password(cls, data: str) -> str: # cls is described as the class to create the Pydantic dataclass from
        return validate_password(data)
    
# Used for updating the user document
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

    @field_validator('password', mode='after') 
    def check_password(cls, data: Optional[str]) -> str:
        if data is None:
            return data
        return validate_password(data)
    
# Used to handle input when creating a new user to avoid manually creating _id
class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

# Pydantic model validator to enforce our specified password requirements
def validate_password(data: str) -> str:
    if len(data) < 8:
        raise ValueError("Password must be at least 8 characters")
    # Should we do a check for special characters?
    return data