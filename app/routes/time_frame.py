from fastapi import APIRouter
from pydantic import BaseModel

from ..models.time_frame import TimeFrame
from ..database.mongodb import database
from ..controllers.time_frame import TimeFrameList

# Setup collection
collection = database.time_frame

# Router
router = APIRouter(prefix="/time_frame", tags=["time_frame"])

# Controllers
list_routes = TimeFrameList(collection)

# Used to handle input when creating a new user to avoid manually creating _id