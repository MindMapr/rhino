
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from ..models.time_frame import TimeFrame, WorkTimeIntervals
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
                start = datetime.combine(start_date, interval.start.timetz()).replace(tzinfo=timezone.utc)
                end   = datetime.combine(start_date, interval.end.timetz()).replace(tzinfo=timezone.utc)
                work_windows_slots.append((start, end))
        start_date += timedelta(days=1)
    return work_windows_slots

def schedule_tasks(tasks: List[Task], work_windows: List[Tuple[datetime, datetime]]) -> List[Task]:
    """
        Pack each task (in ascending priority) into the available work window slots,
        automatically splitting it across multiple work windows if needed and returns a list
    """
    # Sort tasks by ascending priority
    tasks = sorted(tasks, key=lambda t: t.priority)

    # Sort work windows by start time (to ensure time-order)
    work_windows = sorted(work_windows, key=lambda w: w[0])
    
    # Copy work_windows to a mutable list of available slots
    available_slots = list(work_windows)

    for task in tasks:
        remaining = timedelta(hours=task.self_estimated_duration)
        task_start = None
        task_end = None
        i = 0

        while remaining > timedelta(0) and i < len(available_slots):
            window_start, window_end = available_slots[i]
            window_duration = window_end - window_start

            if window_duration <= timedelta(0):
                i += 1
                continue

            # Use as much of this window as needed
            chunk = min(remaining, window_duration)

            if task_start is None:
                task_start = window_start
            task_end = window_start + chunk

            # Update slot to reflect used time
            available_slots[i] = (window_start + chunk, window_end)
            remaining -= chunk

            if available_slots[i][0] >= available_slots[i][1]:
                # Remove fully used slot
                del available_slots[i]
            else:
                i += 1

        if remaining > timedelta(0):
            raise RuntimeError("Not enough available work time to schedule all tasks")

        task.start = task_start
        task.end = task_end

    return tasks


def calculate_tracked_duration(
    start: datetime,
    finished: datetime,
    windows: List[WorkTimeIntervals],
) -> float:
    """
    Return total hours between "start" and "finished",
    including any time outside the given work windows.
    """
    # sort windows by their start
    windows = sorted(windows, key=lambda w: w.start)
    total = timedelta()

    # before the first window
    first = windows[0]
    if start < first.start:
        total += min(finished, first.start) - start

    # Find time inside each window
    for w in windows:
        if finished <= w.start:
            break
        overlap_start = max(start, w.start)
        overlap_end   = min(finished, w.end)
        if overlap_end > overlap_start:
            total += (overlap_end - overlap_start)

    # If task is ending outside a window we include that time
    last = windows[-1]
    if finished > last.end:
        total += (finished - max(start, last.end))

    return total.total_seconds() / 3600
