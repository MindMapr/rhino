from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status
from uuid import UUID
from typing import List, Tuple, Union
from pymongo import UpdateOne

from app.controllers.user import UserList
from ..utils.scheduler import calculate_tracked_duration, generate_available_work_window_slots, schedule_tasks

from ..models.task import Task, UpdateTask
from ..models.time_frame import TimeFrame

# Constants
not_found_404 = "Task not found"

# Helpers
class TaskList():
    def __init__(self, db, time_frame_collection, user_collection):
        self.db = db
        self.time_frame_collection = time_frame_collection
        self.user_collection = user_collection

    def create_task(self, task: Task):
        """
            Creates a new task and uses the scheduler to place the correct start and end time
            of each task based on work windows and priority. When a new task is created this
            is also in charge of potential rescheduling of other tasks in same time frame.
        """
        self.db.insert_one(task.model_dump(by_alias=True))

        # Find all tasks belonging to the given time frame
        all_documents = list(self.db.find({"time_frame_id": task.time_frame_id}))
        tasks = [Task.model_validate(document) for document in all_documents]

        # Find the task  with priority‐1, if it exists
        prev = next(
            (t for t in tasks if t.priority == task.priority - 1),
            None
        )

        now_utc = datetime.now(timezone.utc)

        if prev is None:
            # If there is no priority-1 task, we start from current time
            base_time = now_utc
        else:
            # If it was marked completed, we use actual tracked_time finish; otherwise its scheduled .end
            if prev.completed and prev.tracked_duration is not None:
                actual_finish = prev.start + timedelta(hours=prev.tracked_duration)
            else:
                actual_finish = prev.end

            base_time = max(now_utc, actual_finish)

        # Build work windows from the timeframe:
        time_frame_document = self.time_frame_collection.find_one({"_id": task.time_frame_id})
        time_frame = TimeFrame.model_validate(time_frame_document)
        slots = generate_available_work_window_slots(time_frame)

        # Trim out everything before base_time
        available = self.remaining_work_windows(slots, base_time)

        scheduled = schedule_tasks([task], available)
        new_schedule = scheduled[0]

        # Persist its start & end
        self.db.update_one(
            {"_id": new_schedule.task_id},
            {"$set": {"start": new_schedule.start, "end": new_schedule.end}}
        )

        return new_schedule



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
        """
            Updates a task. If the field contains completed, priority or duration it will also update all other tasks for that time frame to ensure they have the correct time allocated.
        """
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
        if result.matched_count == 0:
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
            # undo completion and zero tracked_duration
            self.handle_uncompletion(task_uuid, existing, time_frame)

            all_tasks = self.find_all_time_frame_tasks(existing.time_frame_id)["data"]
            windows = generate_available_work_window_slots(time_frame)
            # Finding the task where we need to pivot back from before we completed it
            pivot = self.find_specific_task(task_id)

            self.reschedule_downstream_tasks(
                pivot.time_frame_id,
                all_tasks,
                windows,
                pivot
            )

            return pivot
        # Check if priority or duration is updated on one of the tasks and then update all time frame tasks accordingly
        if priority_new != existing.priority or new_estimate != existing.self_estimated_duration:
                updated = self.find_specific_task(task_id)

                time_frame_documents  = self.time_frame_collection.find_one({"_id": updated.time_frame_id})
                time_frame = TimeFrame.model_validate(time_frame_documents)
                original_windows = generate_available_work_window_slots(time_frame)

                # Checks to ensure that priorities are handled correctly, as logic from 1st priority and
                # all others have to be different to keep their correct time slots.
                if priority_new != existing.priority:
                    if updated.priority == 1:
                        original_first = next(
                            t for t in all_tasks
                            if t.task_id != updated.task_id and t.priority == 1
                        )
                        # To ensure that the time is not set back to the beginning of the time frame, but to 
                        # the original start
                        base_time = original_first.start
                    else:
                        # pick up after the new (priority-1)
                        prev = next(
                            t for t in all_tasks
                            if t.priority == updated.priority - 1
                        )
                        # Ensure that the next task is placed correctly depending on if the previous task 
                        # has been completed or not
                        base_time = (
                            (prev.start + timedelta(hours=prev.tracked_duration))
                            if (prev.completed and prev.tracked_duration is not None)
                            else prev.end
                        )

                else:
                    # If no priority was updated then keep the old start time to avoid beginning at the first
                    # work window in time frame
                    base_time = existing.start
                # Ensure we only schedule in free work windows
                free_windows = self.remaining_work_windows(original_windows, base_time)

                # Ensure the schedule is placed at either a free window or take over priority 1s start
                pivot_schedule = schedule_tasks([updated], free_windows)[0]

                self.db.update_one(
                    {"_id": pivot_schedule.task_id},
                    {"$set": {"start": pivot_schedule.start, "end": pivot_schedule.end}}
                )

                self.reschedule_downstream_tasks(
                    updated.time_frame_id,
                    all_tasks,
                    original_windows,
                    pivot_schedule
                )

                return self.find_specific_task(task_id)

    def delete_task(self, task_id: str):
        try:
            uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid task id format")
        to_delete = self.find_specific_task(task_id)

        result = self.db.delete_one({"_id": uuid})
        if not result.deleted_count:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Task not found")

        # Decrement priority of everything that was below the task
        self.db.update_many(
            {
                "time_frame_id": to_delete.time_frame_id,
                "priority": {"$gt": to_delete.priority}
            },
            {"$inc": {"priority": -1}}
        )
        
         # Reload all tasks in that timeframe
        time_frame_documents = list(self.db.find({"time_frame_id": to_delete.time_frame_id}))
        all_tasks = [Task.model_validate(document) for document in time_frame_documents]

        # Split into tasks before and after to ensure we update times correclty
        before = [task for task in all_tasks if task.priority < to_delete.priority]
        after  = [task for task in all_tasks if task.priority >= to_delete.priority]

        # Fetch the TimeFrame and remaining tasks
        time_frame_document = self.time_frame_collection.find_one({"_id": to_delete.time_frame_id})
        time_frame = TimeFrame.model_validate(time_frame_document)

        all_tasks = self.find_all_time_frame_tasks(to_delete.time_frame_id)["data"]

        windows = generate_available_work_window_slots(time_frame)
        windows = self.remaining_work_windows(windows, to_delete.start)

        # Ensure the following tasks only start after actual finished time of an older task 
        for task in sorted(before, key=lambda t: t.priority):
            if task.completed and task.tracked_duration is not None:
                end_time = task.start + timedelta(hours=task.tracked_duration)
            else:
                end_time = task.end
            windows = self.remaining_work_windows(windows, end_time)

        # Schedule the after_tasks into the remaining windows
        scheduled = schedule_tasks(after, windows)
        for task in scheduled:
            utc_start = task.start.astimezone(timezone.utc)
            utc_end   = task.end.astimezone(timezone.utc)

            self.db.update_one(
                {"_id": task.task_id},
                {"$set": {"start": utc_start, "end": utc_end}}
            )

        return {"status": status.HTTP_200_OK, "data": {"deleted_task_id": task_id}}

    ### Helpers for updating to avoid a really bloated update function ###
    
    # Used for finding out how much time is left after finishing. 
    def remaining_work_windows(self, 
        windows: List[Tuple[datetime, datetime]],
        finished_utc: datetime
    ) -> List[Tuple[datetime, datetime]]:
        # Free is the leftover time that might still be if the user finish early.
        free: List[Tuple[datetime, datetime]] = []
        for start, end in windows:
            # Skip the work window if ends before the task is finished
            if end <= finished_utc:
                continue
            # If it finish during the work window, only keep the free part of the work window.
            if start < finished_utc < end:
                free.append((finished_utc, end))
            else:
                free.append((start, end))
        return free

    # Reschedule just the downstream tasks - used when completing a task
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

        free_windows = self.remaining_work_windows(original_window, completed_task.end)
        scheduled = schedule_tasks(to_run, free_windows)
        for task in scheduled:
            utc_start = task.start.astimezone(timezone.utc)
            utc_end   = task.end.astimezone(timezone.utc)

            self.db.update_one(
                {"_id": task.task_id},
                {"$set": {"start": utc_start, "end": utc_end}}
            )
            
        # tnhe logic of how the task is completed. Here we ensure that the tracked_duration is updated
    def handle_completion(self, task_uuid: UUID, existing: Task, time_frame: TimeFrame) -> datetime:
        finished_utc = datetime.now(timezone.utc)
        duration = round(calculate_tracked_duration(
            existing.start,
            finished_utc, 
            time_frame.work_time_frame_intervals,
        ), 2)
        self.db.update_one(
            {"_id": task_uuid},
            {"$set": {"tracked_duration": duration}}
        )
        
        # Ensure the user model is updated as well
        user_id = time_frame.user_id
        pct_error = (duration - existing.self_estimated_duration) / existing.self_estimated_duration * 100
        user_controller = UserList(self.user_collection)
        user_controller.update_user_estimation_average(
            user_id,
            existing.category,
            pct_error
        )
            
        return finished_utc

    # Reset when un-completing
    def handle_uncompletion(self, task_uuid: UUID, existing: Task, time_frame: TimeFrame) -> None:
        # Grab the old pct_error 
        old_pct = round((existing.tracked_duration - existing.self_estimated_duration) / existing.self_estimated_duration * 100)

        # Reset that task’s tracked_duration
        self.db.update_one(
            {"_id": task_uuid},
            {"$set": {"tracked_duration": 0}}
        )

        # Ensure the average and history is removed from the users model
        user_controller = UserList(self.user_collection)
        user_controller.uncomplete_user_estimation_average(
            time_frame.user_id,
            existing.category,
            old_pct,
        )
            
        