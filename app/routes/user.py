from bson import ObjectId
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from ..models.user import User
from ..database.mongodb import database
from ..controllers.user import UserList

# Setup collection
collection = database.user

# Router
router = APIRouter(prefix="/user", tags=["user"])

# Controllers
list_routes = UserList(collection)

@router.post("", status_code=201)
async def create_user(user: User):
    return list_routes.create_user(user)