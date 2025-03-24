from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC
from bson import ObjectId

class Time_frame(BaseModel):
    user: ObjectId._id