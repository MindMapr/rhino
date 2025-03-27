from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, time, date
from uuid import UUID, uuid4

# object containing the time periods during the day, where to user would like to work
class WorkTimeIntervals(BaseModel):
    start: datetime
    end: datetime

    # FIX: pydantic error with values.get. 
    # Check to ensure end date is after start date
    @field_validator("end", mode="after")
    def check_end_after_start(cls, value: datetime, values) -> datetime:
        start = values.get("start")
        if value < start:
            raise ValueError("End date cannot be before start date.")
        return value


class TimeFrame(BaseModel):
    time_frame_id: UUID = Field(default_factory=uuid4, alias="_id") 
    user_id: UUID # id of the user the time frame belongs to
    start_date: datetime = Field(..., description="The date where their project begins")
    end_date: datetime = Field(..., description="The day where they expect their project to end")
    work_time_frame_intervals: list[WorkTimeIntervals] = Field(default=[], description="The work time during the day, where to user would prefer to work")
    include_weekend: bool = Field(default=False, description="Allow the user to decide if they want to include weekends in their schedule")
    created_at: datetime = Field(..., description="To track when time frames are created")