
from datetime import datetime, timedelta
from typing import List, Tuple
from ..models.time_frame import TimeFrame
from ..models.task import Task

# Scheduler is two helper functions used as a tool to ensure the tasks are placed in accordance with the given time-frame's work windows. It takes the start and end date of the users time frame and the work intervals and build into a tuple list. When given a task it looks at priority and in ascending order, split and places the tasks accordingly.

# Helper function for making a list with all dates in time frame and their work window intervals
def generate_available_work_window_slots(time_frame: TimeFrame) -> List[Tuple[datetime, datetime]]:
    """
        Takes a time frames start and end date along with it work time intervals. 
        Creates a where each entry it is a tuple of start and end time of format 2025-04-20T08:00:00
    """
    # Create an empty list to contain a list where each element is a work window interval
    work_windows_slots: List[Tuple[datetime, datetime]] = []
    # Finds the start and end date of the time frame
    start_date = time_frame.start_date.date()
    end_date = time_frame.end_date.date()
    while start_date <= end_date:
        # Check if time frame also includes weekends otherwise it will only take monday to friday into account
        if time_frame.include_weekend or start_date.weekday() < 5:
            # Loops through each of our work window intervals
            for interval in time_frame.work_time_frame_intervals:
                # Combines a date in the time frame with the work intervals - it creates a string like this 2025-04-20T08:00:00
                start = datetime.combine(start_date, interval.start.time())
                end   = datetime.combine(start_date, interval.end.time())
                work_windows_slots.append((start, end))
        start_date += timedelta(days=1)
    return work_windows_slots

def schedule_tasks(tasks: List[Task], work_windows: List[Tuple[datetime, datetime]]) -> List[Task]:
    """
        Pack each task (in ascending priority) into the available work window slots,
        automatically splitting it across multiple work windows if needed and returns a list
    """
    # sort by priority
    tasks = sorted(tasks, key=lambda t: t.priority)

    # Uses a python iterator called iter, works on list, dicts and tuples. Can use the Pythons next to iteratre through them.
    iterate_through_work_window_slots = iter(work_windows)
    # Try to iterate through the work windows, unless there are none
    try:
        current_start, current_end = next(iterate_through_work_window_slots)
    except StopIteration:
        raise RuntimeError("No work windows")

    for task in tasks:
        # Keeping track of how much of the task still needs to be allocated time
        remaing_time_left_on_task = timedelta(hours=task.duration)
        task_start = None

        # Continue to go through task until there are no more to schedule
        while remaing_time_left_on_task > timedelta(0):
            # if no more time left in work window we try to continue to the next work window, as long as it exists 
            if current_start >= current_end:
                try:
                    current_start, current_end = next(iterate_through_work_window_slots)
                except StopIteration:
                    raise RuntimeError("Not enough available work time to schedule all tasks")

            if task_start is None:
                task_start = current_start

            # Looks at how much time is left in the current work window
            available_left_in_window = current_end - current_start
            # Checks where there is less time. If there is less time left on task than what is available in current window, it will be assigned to the variable or the other way around.
            chunk = min(remaing_time_left_on_task, available_left_in_window)
            current_start += chunk
            remaing_time_left_on_task -= chunk

        # Add the correct start and end time to the tasks
        task.start = task_start
        task.end   = current_start

    return tasks
