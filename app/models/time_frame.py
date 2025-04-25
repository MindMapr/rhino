import re
from pydantic import BaseModel, Field, field_validator,  model_validator
from typing import Optional
from datetime import datetime, date
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

    # Important that mode is set to before to confirm input. Used to ensure the database
    # receives the correct input when adding a WorkTimeInterval in frontend, as it is send as hh:mm.
    @field_validator("start", "end", mode="before")
    def add_date_if_only_time(cls, value):
        # Check if value is a string without date/only with time
        if isinstance(value, str) and re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", value):
            # Use today's date
            default_date = date.today().isoformat()
            # Ensure seconds is also included in the iso string
            if len(value.split(":")) == 2:
                value = f"{value}:00"
            # Combine the default date with the time string and add the "Z" suffix for UTC.
            value = f"{default_date}T{value}Z"
        return value


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
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_weekend: Optional[bool] = None

class CreateTimeFrame(BaseModel):
    start_date: date
    end_date: date
    work_intervals: list[WorkTimeIntervals]
    include_weekend: bool
