from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Annotated
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from dotenv import load_dotenv
import os

from ..models.user import User, UserUpdate, CreateUserRequest
from ..database.mongodb import database as db
from ..controllers.user import UserList
import app.utils.auth as auth

load_dotenv()
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))

# Setup collection
collection = db.user

# Router
router = APIRouter(prefix="/user", tags=["user"])

# Controllers
list_routes = UserList(collection)

# Dependencies
user_dependency = Annotated[dict, Depends(auth.get_current_user)]

@router.get("/all_users", description="Find all users")
async def get_all_users():
    return list_routes.get_all_users()

@router.get("", description="Find specific user with their id")
async def get_user(current_user: user_dependency):
    user_id = current_user["_id"]
    return list_routes.get_user(user_id)

@router.post("", status_code=201, description="Create a new user")
async def create_user(params: CreateUserRequest):
    try:
    # Convert user request into an instance of user
        user = User(**params.model_dump())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters"
        )
    return list_routes.create_user(user)

@router.post("/login", response_model=auth.Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response):
    # Ensure user exists in database
    user = list_routes.authenticate_user(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user"
        )
    # Create the tokens based on the logic from the auth-file
    access_token = auth.create_access_token(user.username, user.user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = auth.create_refresh_token(user.username, user.user_id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    # response = JSONResponse(
    #     content={"access_token": access_token, "token_type": "bearer"}
    # )
    # For prod
    # response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", domain="mindmapr-planner.vercel.app", path="/")
    # response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", domain="mindmapr-planner.vercel.app", path="/")
    # For dev
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout_for_access_token(dependencies: user_dependency, response: Response):
    # Ensures both cookies are deleted when the user logs out
    # For DEV
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    # For PROD
    # response.delete_cookie(key="access_token", path="/", domain="mindmapr-planner.vercel.app", secure=True, samesite="none")
    # response.delete_cookie(key="refresh_token", path="/", domain="mindmapr-planner.vercel.app", secure=True, samesite="none")


@router.put("", description="Update user information")
async def update_user(user: UserUpdate, current_user: user_dependency):
    user_id = current_user["_id"]
    return list_routes.update_user(user_id, user)

@router.delete("", description="Permantly delete a user - approach with caution")
async def delete_user(current_user: user_dependency):
    user_id = current_user["_id"]
    return list_routes.delete_user(user_id)

# This endpoint is only used on routes in frontend that we do not have a backend point to
@router.post("/protected")
async def protected_route(dependecies: Annotated[dict, Depends(auth.get_current_user_with_refresh)], response: Response = None):
    return {"msg": "success"}
