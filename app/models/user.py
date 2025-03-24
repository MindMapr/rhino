from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC
from ..utils.parse_objectId import PydanticObjectId

# User schema
class User(BaseModel):
    model_config = {
        "populate_by_name": True
    }
    user_id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id") 
    username: str
    email: str
    password: str
    created_at: datetime = Field(default_factory = lambda: datetime.now(UTC))
    # TODO: add profile image?

    # Pydantic model validator to enforce our specified password requirements
    @field_validator('password', mode='after') 
    def validate_password(cls, data: str) -> str: # cls is described as the class to create the Pydantic dataclass from
        if len(data) < 8:
            raise ValueError("Password must be at least 8 characters")
        # Should we do a check for special characters?
        return data
    
    # TODO: add field_validator for email - confirm @ etc.