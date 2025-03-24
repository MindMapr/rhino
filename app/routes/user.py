from fastapi import APIRouter
from pydantic import BaseModel

from ..models.user import User, UserUpdate
from ..database.mongodb import database
from ..controllers.user import UserList

# Setup collection
collection = database.user

# Router
router = APIRouter(prefix="/user", tags=["user"])

# Controllers
list_routes = UserList(collection)

# Used to handle input when creating a new user to avoid manually creating _id
class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str


@router.get("/{user_id}")
async def get_user(user_id: str):
    return list_routes.get_user(user_id)

@router.post("", status_code=201)
async def create_user(params: CreateUserRequest):
    # Convert user request into an instance of user
    user = User(**params.model_dump())
    return list_routes.create_user(user)

@router.put("/{user_id}")
async def update_user(user_id: str, user: UserUpdate):
    return list_routes.update_user(user_id, user)

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    return list_routes.delete_user(user_id)