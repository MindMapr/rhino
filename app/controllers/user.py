# Imports
from fastapi import HTTPException, status
from typing import List
from uuid import UUID

# Utils
from ..utils.hasher import Hasher

# Models
from ..models.user import User, UserUpdate

# Constants
not_found_404 = "User not found"

# Helpers
class UserList:
    def __init__(self, db):
        self.db = db

    # Find all users in the collection and return them as a list
    def get_all_users(self) -> List[User]:
        """
            Get all users in database, returns a list
        """
        result = self.db.find()
        number_of_users = self.db.count_documents({})
        return {
            "status": status.HTTP_200_OK,
            "meta": number_of_users, # prints the amount of users in the collection - only metadata, so cannot be used in FE
            "data": [User(**user) for user in result]
        }

    def get_user(self, user_id: str):
        """
            Get a single user based on their id
        """
        result = self.db.find_one({"_id": UUID(user_id)})
        if result:
            return {
                "status": status.HTTP_200_OK,
                "data": User(**result)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404
            )
    
    # Used in auth for token validation
    def get_user_by_username(self, username: str):
        """
            Get a single user based on their username
        """
        result = self.db.find_one({"username": username})
        if result:
            return User(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404
            )
    
    
    def authenticate_user(self, username: str, password: str):
        """
            Takes the users usernamer and passowrd, verify the hased password and returns the user
        """
        user = self.get_user_by_username(username=username)
        if not user:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        if not Hasher.verify_password(plain_password=password, hashed_password=user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )
        return user

    def create_user(self, user: User):
        """
            Hashes the users password and adds them to the database
        """
        # check if username or email is already taken
        self.check_username_and_email(user)

        # Hashing password with bcrypt from CryptContext
        hashed_password = Hasher.get_password_hash(user.password)
        user.password = hashed_password

        _ = self.db.insert_one(user.model_dump(by_alias=True))

    def update_user(self, user_id: str, user: UserUpdate):
        """
            Can update the username, email or password of the user. 
            If the user updates their password it will be hashed before storing it.
        """
        self.check_username_and_email(user)

        update_field = user.model_dump(exclude_unset=True)
        # Ensure updated password is still hashed
        if "password" in update_field:
            update_field["password"] = Hasher.get_password_hash(user.password)

        result = self.db.update_one(
                {"_id": UUID(user_id)},
                {"$set": update_field}
            )
        if result.modified_count:
            return {
                "status": status.HTTP_200_OK,
                "data": {"user": str(result)}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404
            )


    # Delete user from database
    def delete_user(self, user_id: str):
        """
            Deletes a user from the database based on their id
        """
        result = self.db.delete_one({"_id": UUID(user_id)})
        if result.deleted_count:
            return {
                "status": status.HTTP_200_OK,
                "data": {"user": str(result)}
            }
        else:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = not_found_404
            )

    def check_username_and_email(self, user):
        """
            Checks if username or email is already used in the database. Returns 400 if they are taken.
        """
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
