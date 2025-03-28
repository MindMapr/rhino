from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class TaskCategory(str, Enum):
    reading = "reading"
    writing = "writing"
    research = "research"
    coding = "coding"
    lecture = "lecture"
    group_meeting = "group meeting"
    # can't think of anymore, feel free to add


class Task(BaseModel):
    task_id: UUID = Field(default_factory=uuid4, alias="_id")
    time_frame_id: UUID = Field(..., description="ID for the time_frame the task belongs to")
    title: str = Field(..., description="The title of the task")
    priority: int = Field(..., description="The priority of the task that needs to be completed") # maybe do a check between 1-5?
    duration: float = Field(..., description="How long the task is estimated to take")
    start: datetime = Field(..., description="The expected start of the task")
    end: datetime = Field(..., description="The expected end of task")
    category: TaskCategory = Field(..., description="The category type of the task")
    description: Optional[str] = "" # Should we do None or empty string?
    completed: bool = Field(default=False, description="Check if task has been completed")

class UpdateTask(BaseModel):
    title: Optional[str] = None
    priority: Optional[int] = None
    duration: Optional[float] = None
    start: Optional[datetime] = None
    category: Optional[TaskCategory] = None
    description: Optional[str] = None 
    completed: Optional[bool] = None 