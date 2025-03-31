from fastapi import APIRouter, Depends
from typing import Annotated
from datetime import timedelta

from ..models.task import Task, UpdateTask, CreateTask
from ..database.mongodb import database
from ..controllers.task import TaskList
from ..utils.auth import get_current_user

# Setup collection
collection = database.task

# Router
router = APIRouter(prefix="/task", tags=["task"])

# Controllers
list_routes = TaskList(collection)

# Dependencies
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.post("/{time_frame_id}", status_code=201)
async def create_task(time_frame_id: str, params: CreateTask, current_user: user_dependency):
    task = Task(
        time_frame_id=time_frame_id,
        title=params.title,
        priority=params.priority,
        duration=params.duration,
        start=params.start,
        end=(params.start + timedelta(hours=params.duration)), # We need to figure out how duration is handled in frontend
        category=params.category,
        description=params.description
    )

    return list_routes.create_task(task)

@router.get("/{time_frame_id}/find_all", description="Find all tasks for time frame")
async def find_all_time_frame_tasks(time_frame_id: str, current_user: user_dependency):
    return list_routes.find_all_time_frame_tasks(time_frame_id)

@router.get("/{id}", description="Find specific task")
async def find_specific_task(task_id: str, current_user: user_dependency):
    return list_routes.find_specific_task(task_id)

@router.put("/{id}", description="Update a task")
async def update_task(task_id: str, task: UpdateTask, current_user: user_dependency):
    return list_routes.update_task(task_id, task)

@router.delete("/{}", description="Delete the task")
async def delete_task(task_id: str, current_user: user_dependency):
    return list_routes.delete_task(task_id)