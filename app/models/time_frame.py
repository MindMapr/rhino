from pydantic import BaseModel, Field,  model_validator
from datetime import datetime
from uuid import UUID, uuid4

# object containing the time periods during the day, where to user would like to work
class WorkTimeIntervals(BaseModel):
    start: datetime
    end: datetime

    # Check to ensure end time is after start time
    @model_validator(mode="after")
    def verify_work_intervals_starts_before_ends(cls, model):
        if model.end < model.start:
            raise ValueError("End time cannot be before your start time.")
        return model


class TimeFrame(BaseModel):
    time_frame_id: UUID = Field(default_factory=uuid4, alias="_id") 
    user_id: UUID # id of the user the time frame belongs to
    start_date: datetime = Field(..., description="The date where their project begins")
    end_date: datetime = Field(..., description="The day where they expect their project to end")
    work_time_frame_intervals: list[WorkTimeIntervals] = Field(default=[], description="The work time during the day, where to user would prefer to work")
    include_weekend: bool = Field(default=False, description="Allow the user to decide if they want to include weekends in their schedule")
    created_at: datetime = Field(..., description="To track when time frames are created")

# Should we allow for updates in work_time_frame_intervals? Could imagine it could get quite complex
class UpdateTimeFrame(BaseModel):
    start_date: datetime
    end_date: datetime
    include_weekend: bool