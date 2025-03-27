from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from ..database.mongodb import database as db

# Based on fastapi document for oauth:
# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#handle-jwt-tokens
# And on Eric Robys video:
# https://www.youtube.com/watch?v=0A_GCXBCNUQ&t=14s

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

# FIX: the prefix should not be hard-coded in here, should come from main
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/user/login")

class Token(BaseModel):
    access_token: str
    token_type: str



def create_access_token(username: str, user_id: str, expires_delta: timedelta):
    encode = {"sub": username, "_id": str(user_id)}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expires})
    encoded_jwt = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("_id")
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user: {username}, {user_id}"
            )
        return {"username": username, "_id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user because of jwt: {username}, {user_id}"
        )
