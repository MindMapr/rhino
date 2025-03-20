from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC

# User schema
class User(BaseModel):
    username: str
    email: str
    password: str
    created_at: datetime = Field(default_factory = lambda: datatime.now(UTC))
    # TODO: add profile image?

    # Pydantic model validator to enforce our specified password requirements
    @field_validator('password', mode='after')
    def validate_password(cls, data: str) -> str: # cls is described as the class to create the Pydantic dataclass from
        if len(data) < 8:
            raise ValueError("Password must be at least 8 characters")
        # Should we do a check for special characters?
        return data
    
    # TODO: add field_validator for email - confirm @ etc.