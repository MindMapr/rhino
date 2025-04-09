from datetime import datetime, timedelta, timezone
from typing import Annotated

from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from ..utils.oauth_cookies import OAuth2PasswordBearerWithCookie

# Based on fastapi document for oauth:
# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#handle-jwt-tokens
# And on Eric Robys video:
# https://www.youtube.com/watch?v=0A_GCXBCNUQ&t=14s

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# FIX: the prefix should not be hard-coded in here, should come from main
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/v1/user/login")

class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(username: str, user_id: str, expires_delta: timedelta):
    encode = {"sub": username, "_id": str(user_id)}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expires})
    encoded_jwt = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    print(encoded_jwt)
    return encoded_jwt

# Refresh token is based on this article: 
# https://gh0stfrk.medium.com/token-based-authentication-with-fastapi-7d6a22a127bf
def create_refresh_token(username: str, user_id: str, expires_delta: timedelta):
    payload = {
        "sub": username, 
        "_id": str(user_id)
    }
    expires = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": expires})
    refresh_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return refresh_jwt

def refresh_for_new_access_token(refresh_token: str):
    if refresh_token in blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token available"
        )
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("_id")
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        new_access_token = create_access_token(username, user_id, timedelta(seconds=ACCESS_TOKEN_EXPIRE_MINUTES))
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT Error: Invalid refresh token"
        )

# Consider using redis for blacklisted tokens - best approach
# Or just a document in our MongoDB
# blacklist is for storing invalid tokens, used for logout
# Based on https://www.restack.io/p/fastapi-logout-answer
# TODO: blacklist refresh tokens
blacklist = set()

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    # currently not using blacklist
    # if token in blacklist:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Token has been revoked"
    #     )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("_id")
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user"
            )
        return {"username": username, "_id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user"
        )

# Currently unsure if this actually works - and if we should keep it
# Right now the logout endpoint deletes the cookies. Should we stick to that or blacklist?
# async def logout(token: Annotated[str, Depends(oauth2_scheme)]):
#     blacklist.add(token)
#     print(blacklist)
#     # TODO: delete cookie
#     return {"msg": "Successfully logged out"}