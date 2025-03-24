from pydantic import BaseModel, Field, field_validator
from datetime import datetime, UTC
from ..utils.parse_objectId import PydanticObjectId

# object containing the time periods during the day, where to user would like to work
class Work_time_intervals(BaseModel):
    hello: str


class Time_frame(BaseModel):
    time_frame_id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id") 
    user_id: PydanticObjectId # id of the user the time frame belongs to
    start_date: datetime = Field(..., description="The date where their project begins")
    end_date: datetime = Field(..., default="The day where they expect their project to end")
    work_time_frame_intervals: list[Work_time_intervals] = Field(default=[], description="The work time during the day, where to user would prefer to work")
    include_weekend: bool = Field(..., default=False)