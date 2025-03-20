from bson import ObjectId
from fastapi import HTTPException, status

from ..utils.hasher import Hasher
from ..models.user import User

class UserList:
    def __init__(self, db):
        self.db = db

    def create_user(self, user: User):
        # Check if username already exists
        if self.db.find_one({"username": user.username}):
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "Username already taken"
            )
        
        # Check if email already exists
        if self.db.find_one({"email": user.email}):
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "Email already taken"
            )

        # Hashing password with bcrypt from CryptContext
        hashed_password = Hasher.get_password_hash(user.password)
        user.password = hashed_password
        
        _ = self.db.insert_one(user.model_dump(by_alias=True))
