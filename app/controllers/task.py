from fastapi import HTTPException, status
from uuid import UUID
from typing import List
from datetime import timedelta

from ..models.task import Task, UpdateTask

# Constants
not_found_404 = "Task not found"

# Helpers
class TaskList():
    def __init__(self, db):
        self.db = db

    def create_task(self, task: Task):
        # end is the start + duration
        _ = self.db.insert_one(task.model_dump(by_alias=True))
    
    def find_all_time_frame_tasks(self, time_frame_id: str) -> List[Task]:
        # Right now it returns an error if it is empty
        result = list(self.db.find({"time_frame_id": UUID(time_frame_id)}))

        if result:
            return {
                "status": status.HTTP_200_OK,
                "data": [Task(**task) for task in result]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No task found for time_frame"
            )
        
    def find_specific_task(self, task_id: str):
        result = self.db.find_one({"_id": UUID(task_id)})

        if result:
            return Task(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No task found"
            )
        
    def update_task(self, task_id: str, task: UpdateTask):
        update_field = task.model_dump(exclude_unset=True)

        # Ensure the end time is change if start or duration changes
        if "start" or "duration" in update_field:
            updated_task = self.find_specific_task(task_id)
            
            new_start = update_field.get("start", updated_task.start)
            new_duration = update_field.get("duration", updated_task.duration)
            
            update_field["end"] = new_start + timedelta(hours=new_duration)
            

        result = self.db.update_one(
                {"_id": UUID(task_id)},
                {"$set": update_field}
            )
        if result.modified_count:
            return {
                "status": status.HTTP_200_OK,
                "data": {"user": str(result)}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404
            )

    def delete_task(self, task_id: str):
        result = self.db.delete_one({"_id": UUID(task_id)})
        if result.deleted_count:
            return {
                "status": status.HTTP_200_OK,
                "data": {"task": str(result)}
            }
        else:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = not_found_404
            )