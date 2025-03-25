from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, UTC
# from ..utils.parse_objectId import PydanticObjectId

# User schema
class User(BaseModel):
    user_id: UUID = Field(default_factory=uuid4, alias="_id") 
    username: str
    email: EmailStr
    password: str
    created_at: datetime = Field(default_factory = lambda: datetime.now(UTC))
    # SUGGESTION: Maybe a personal enum for task they create, that we do not have?
    # TODO: add profile image?

    
    @field_validator('password', mode='after') 
    def check_password(cls, data: str) -> str: # cls is described as the class to create the Pydantic dataclass from
        return validate_password(data)
    
    # TODO: add field_validator for email - confirm @ etc.

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

# Pydantic model validator to enforce our specified password requirements
def validate_password(data: str) -> str:
    if len(data) < 8:
        raise ValueError("Password must be at least 8 characters")
    # Should we do a check for special characters?
    return data