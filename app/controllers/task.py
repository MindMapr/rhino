from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from uuid import UUID
from typing import List, Tuple, Union
from pymongo import UpdateOne
from ..utils.scheduler import calculate_tracked_duration, generate_available_work_window_slots, schedule_tasks

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
            Creates a new task and uses the scheduler to place the correct start and end time
            of each task based on work windows and priority. When a new task is created this
            is also in charge of potential rescheduling of other tasks in same time frame.
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
        # validate and pull existing task
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid task id format")
        existing = self.find_specific_task(task_id)

        # Update and check that it succeeded
        update_field = task.model_dump(exclude_unset=True)
        result = self.db.update_one({"_id": task_uuid}, {"$set": update_field})
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=not_found_404
            )

        # Gettubg everything ready to be able to handle the duration and work window logic updates.
        # First we find the time frame and validates it
        time_frame_document = self.time_frame_collection.find_one({"_id": existing.time_frame_id})
        time_frame = TimeFrame.model_validate(time_frame_document)
        # Find all tasks belonging to the model so it is ready for when start and end times needs to be updated.
        all_responses = self.find_all_time_frame_tasks(existing.time_frame_id)
        all_tasks: List[Task] = all_responses["data"]
        original_windows = generate_available_work_window_slots(time_frame)

        # These are used as temp variables to help selective checks later
        completed = update_field.get("completed", existing.completed)
        priority_new = update_field.get("priority", existing.priority)
        new_estimate = update_field.get("self_estimated_duration", existing.self_estimated_duration)

        # Check to see if completed is what is being updated, and it is set to true, but also ensure 
        # that it is not already set to true to avoid uneeded calls to the database.
        if "completed" in update_field and completed and not existing.completed:
            finished_utc = self.handle_completion(task_uuid, existing, time_frame)
            # Takes the existing task but only overrides the end field. This is just to have a copy 
            # of the task with the actual end time and not estimated end time, that we can then use to reschedule all the
            # other tasks to have the correct end time based on what the actual end time of the task was, without having 
            # to change the end time for the task so that can be used for later research if needed
            completed_task = existing.model_copy(update={"end": finished_utc})
            # Reschedule downstream tasks
            self.reschedule_downstream_tasks(existing.time_frame_id, all_tasks, original_windows, completed_task)
            return self.find_specific_task(task_id)

        # Check to update if complete is being updated to false and then reschedule tasks back to the original estimate
        if "completed" in update_field and not completed and existing.completed:
                self.handle_uncompletion(task_uuid)

                # Find the tasks belonging to that time frame and update their times to match the work windows
                all_tasks = self.find_all_time_frame_tasks(existing.time_frame_id)["data"]
                windows   = generate_available_work_window_slots(time_frame)

                self.reschedule_all_tasks(all_tasks, windows)
                return self.find_specific_task(task_id)

        # Check if priority of duration is updated on one of the tasks and then update all time frame tasks accordingly
        if priority_new != existing.priority or new_estimate != existing.self_estimated_duration:
            self.reschedule_all_tasks(all_tasks, original_windows)
            return next(task for task in self.find_all_time_frame_tasks(existing.time_frame_id)["data"]
                        if task.task_id == task_uuid)

        # Return the orignal task that is being updated
        return self.find_specific_task(task_id)

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

    ### Helpers for updating to avoid a really bloated long update function ###
    
    def carve_free_windows(self, 
        windows: List[Tuple[datetime, datetime]],
        finished_utc: datetime
    ) -> List[Tuple[datetime, datetime]]:
        free: List[Tuple[datetime, datetime]] = []
        for start, end in windows:
            if end <= finished_utc:
                continue
            if start < finished_utc < end:
                free.append((finished_utc, end))
            else:
                free.append((start, end))
        return free

    # 2) Reschedule just the downstream tasks
    def reschedule_downstream_tasks(
        self,
        time_frame_id: UUID,
        all_tasks: List[Task],
        original_window: List[Tuple[datetime, datetime]],
        completed_task: Task,
    ) -> None:
        # filter to not-yet-completed, lower-priority tasks
        to_run = [
            task for task in all_tasks
            if task.priority > completed_task.priority and not task.completed
        ]

        free_windows = self.carve_free_windows(original_window, completed_task.end)
        scheduled = schedule_tasks(to_run, free_windows)
        for t in scheduled:
            self.db.update_one({"_id": t.task_id}, {"$set": {"start": t.start, "end": t.end}})

    # 3) Full reschedule of *all* tasks
    def reschedule_all_tasks(
        self,
        all_tasks: List[Task],
        orig_windows: List[Tuple[datetime, datetime]],
    ) -> None:
        scheduled = schedule_tasks(all_tasks, orig_windows)
        for t in scheduled:
            self.db.update_one({"_id": t.task_id}, {"$set": {"start": t.start, "end": t.end}})
            
    def handle_completion(
        self,
        task_uuid: UUID,
        existing: Task,
        time_frame: TimeFrame
    ) -> datetime:
        finished_local = datetime.now(tz=ZoneInfo("Europe/Copenhagen"))
        finished_utc   = finished_local.astimezone(timezone.utc)
        duration = calculate_tracked_duration(
            existing.start,
            finished_utc + timedelta(hours=2), # Sorry, I am tired and I can only get it to work by hard coding it
            time_frame.work_time_frame_intervals,
        )
        self.db.update_one(
            {"_id": task_uuid},
            {"$set": {"tracked_duration": duration}}
        )
        return finished_utc

    # 5) Reset when un-completing
    def handle_uncompletion(self, task_uuid: UUID) -> None:
        self.db.update_one({"_id": task_uuid}, {"$set": {"tracked_duration": 0}})