from fastapi import HTTPException, status
from uuid import UUID
from typing import List, Union
from pymongo import UpdateOne
from ..utils.scheduler import generate_available_work_window_slots, schedule_tasks

from ..models.task import Task, UpdateTask
from ..models.time_frame import TimeFrame

# Constants
not_found_404 = "Task not found"

# Helpers
class TaskList():
    def __init__(self, db, time_frame_collection):
        self.db = db
        self.time_frame_collection = time_frame_collection

    def create_task(self, task: Task):
        """
            Creates a new task and uses the scheduler to place the correct start and end time of each task based on work windows and priority. When a new task is created this is also in charge of potential rescheduels of other tasks in same time frame.
        """
        _ = self.db.insert_one(task.model_dump(by_alias=True))
        
        # Find all tasks belonging to the given time frame
        response = self.find_all_time_frame_tasks(task.time_frame_id)
        # Since find_all_time_frame_tasks return both status and data, we specify we are only interested in data here.
        tasks: List[Task] = response["data"]
        
        time_frame_data = self.time_frame_collection.find_one(task.time_frame_id)
        # Validate it as a pydantic model instance
        time_frame = TimeFrame.model_validate(time_frame_data)
        
        available_work_time = generate_available_work_window_slots(time_frame)
        schedule = schedule_tasks(tasks, available_work_time)
        
        # Loops through the tasks and update their work times if needed
        for scheduling_tasks in schedule:
            self.db.update_one({"_id": scheduling_tasks.task_id}, {"$set": {"start": scheduling_tasks.start, "end": scheduling_tasks.end}})
        
        # Only return the newest created task, not all of them
        return next(new_task for new_task in schedule if new_task.task_id == task.task_id)
        
    
    
    def find_all_time_frame_tasks(self, time_frame_id: Union[str, UUID]) -> dict:
        """
        Returns all tasks for a given time_frame_id, or 404 if none exist.
        """
        # Ensure we have a UUID, otherwise we get an error when creating a new task
        if isinstance(time_frame_id, str):
            try:
                time_frame_uuid = UUID(time_frame_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid time frame id format"
                )
        else:
            time_frame_uuid = time_frame_id

        # Creates a list of all tasks belonging to the time frame
        docs = list(self.db.find({"time_frame_id": time_frame_uuid}))
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tasks found in this time frame"
            )

        # Turn documents into a task model
        tasks = [Task.model_validate(document) for document in docs]
        return {
            "status": status.HTTP_200_OK, 
            "data": tasks
        }
        
    def find_specific_task(self, task_id: str):
        """
            Find a specific task based on the provided id
        """
        result = self.db.find_one({"_id": UUID(task_id)})

        if result:
            return Task(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No task found"
            )
        
    # TODO: We need to fix the update tasks and creation of a new one. Currently, it does work, but if a user suddenly has a lot of tasks and we call all of them individual to update them, it can potentially create bottlenecks.
    def update_task(self, task_id: str, task: UpdateTask) -> Task:
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task id format"
            )
        # Find the existing task to get the id from the time frame
        existing = self.find_specific_task(task_id)        
        
        update_field = task.model_dump(exclude_unset=True)
        
        result = self.db.update_one(
                {"_id": UUID(task_id)},
                {"$set": update_field}
            )
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404
            )
        response = self.find_all_time_frame_tasks(existing.time_frame_id)
        tasks: List[Task] = response["data"]

        # 7) Load the user's TimeFrame settings
        time_frame_document = self.time_frame_collection.find_one({"_id": existing.time_frame_id})
        time_frame = TimeFrame.model_validate(time_frame_document)

        # 8) Generate slots and run the scheduler
        slots     = generate_available_work_window_slots(time_frame)
        scheduled = schedule_tasks(tasks, slots)

        # 9) Persist each task's new start/end
        for t in scheduled:
            self.db.update_one(
                {"_id": t.task_id},
                {"$set": {"start": t.start, "end": t.end}}
            )

        # 10) Return the one we just updated
        return next(t for t in scheduled if t.task_id == existing.task_id)    

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