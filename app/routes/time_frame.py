from fastapi import APIRouter, Response
from pydantic import BaseModel
from datetime import datetime, date, time

from ..models.time_frame import TimeFrame, WorkTimeIntervals
from ..models.user import User
from ..database.mongodb import database
from ..controllers.time_frame import TimeFrameList

# Setup collection
collection = database.time_frame

# Router
router = APIRouter(prefix="/time_frame", tags=["time_frame"])

# Controllers
list_routes = TimeFrameList(collection)

class CreateTimeFrame(BaseModel):
    start_date: date
    end_date: date
    work_intervals: WorkTimeIntervals
    include_weekend: bool

@router.post("", status_code=201)
async def create_time_frame(params: CreateTimeFrame, user: User):
    # Converting the request to an instance of time_frame. Using this approach instead of model_dump to ensure user_id is included
    time_frame = TimeFrame(
        user = user.user_id,
        start_date=params.start_date,
        end_date=params.end_date,
        work_time_frame_intervals=params.work_intervals,
        include_weekend=params.include_weekend
    )                            
    return list_routes.create_time_frame(time_frame)