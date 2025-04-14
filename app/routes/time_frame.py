from fastapi import APIRouter, Depends
from typing import Annotated
from datetime import datetime, timezone

from ..models.time_frame import TimeFrame, UpdateTimeFrame, CreateTimeFrame
from ..database.mongodb import database
from ..controllers.time_frame import TimeFrameList
from ..utils.auth import get_current_user

# Setup collection
collection = database.time_frame

# Router
router = APIRouter(prefix="/time_frame", tags=["time_frame"])

# Controllers
list_routes = TimeFrameList(collection)

# Dependencies
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.post("", status_code=201)
async def create_time_frame(params: CreateTimeFrame, current_user: user_dependency):
    # Converting the request to an instance of time_frame. Using this approach instead of model_dump to ensure user_id is included
    time_frame = TimeFrame(
        user_id = current_user["_id"],
        start_date=params.start_date,
        end_date=params.end_date,
        work_time_frame_intervals=params.work_intervals,
        include_weekend=params.include_weekend,
        created_at=datetime.now(timezone.utc)
    )
    print(time_frame)                    
    return list_routes.create_time_frame(time_frame)

# Consider if it should be protected?
@router.get("/all_time_frames", description="Find all time frames in database")
async def get_all_time_frames():
    return list_routes.get_all_time_frames()

@router.get("/", description="Find a specific time frame based on a given time frame id")
async def get_single_time_frame(time_frame_id: str, current_user: user_dependency):
    return list_routes.get_single_time_frame(time_frame_id)

@router.get("/all_user_time_frames", description="Find all time frames from a specific user")
async def get_all_user_specific_time_frames(current_user: user_dependency):
    return list_routes.get_all_user_specific_time_frames(current_user["_id"])

@router.get("/find_active_time_frame", description="Find the current active time frame belonging to the user")
async def get_active_time_frame(current_user: user_dependency):
    return list_routes.get_active_time_frame(current_user["_id"])

@router.put("/", description="Update a specific time_frame")
async def update_time_frame(time_frame_id: str, time_frame: UpdateTimeFrame, current_user: user_dependency):
    return list_routes.update_time_frame(time_frame_id, time_frame)

@router.delete("/{id}")
async def delete_time_frame(time_frame_id: str, current_user: user_dependency):
    return list_routes.delete_time_frame(time_frame_id)