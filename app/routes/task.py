from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated
from datetime import timedelta

from ..models.task import Task, UpdateTask, CreateTask
from ..database.mongodb import database
from ..controllers.task import TaskList
from ..controllers.user import UserList
from ..utils.auth import get_current_user

# Setup collection
collection = database.task
time_frame_collection = database.time_frame
user_collection = database.user

# Router
router = APIRouter(prefix="/task", tags=["task"])

# Controllers
list_routes = TaskList(collection, time_frame_collection, user_collection)

# Dependencies
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.post("/{time_frame_id}", status_code=201)
async def create_task(time_frame_id: str, params: CreateTask, current_user: user_dependency, confirm: bool = Query(False)):
    user = UserList(user_collection)
    suggest = user.suggestion_estimation(current_user["_id"], params.category, params.self_estimated_duration, confirm)
    
    if suggest is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=suggest
        )
    
    task = Task(
        time_frame_id=time_frame_id,
        title=params.title,
        priority=params.priority,
        self_estimated_duration=params.self_estimated_duration,
        tracked_duration=0,
        start=params.start,
        end=(params.start + timedelta(hours=params.self_estimated_duration)),
        category=params.category,
        description=params.description or ""
    )

    return list_routes.create_task(task)

@router.get("/{time_frame_id}/find_all", description="Find all tasks for time frame")
async def find_all_time_frame_tasks(time_frame_id: str, current_user: user_dependency):
    return list_routes.find_all_time_frame_tasks(time_frame_id)

@router.get("/{id}", description="Find specific task")
async def find_specific_task(task_id: str, current_user: user_dependency):
    return list_routes.find_specific_task(task_id)

@router.put("/{task_id}", description="Update a task")
async def update_task(task_id: str, task: UpdateTask, current_user: user_dependency):
    return list_routes.update_task(task_id, task)

@router.delete("/{id}", description="Delete the task")
async def delete_task(task_id: str, current_user: user_dependency):
    return list_routes.delete_task(task_id)
