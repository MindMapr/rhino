from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from jose import jwt, JWTError
from fastapi import Cookie, Depends, HTTPException, Response, status
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


# Setup and encoding of tokens
def create_access_token(username: str, user_id: str, expires_delta: timedelta):
    # This is were the payload is created
    encode = {"sub": username, "_id": str(user_id)}
    # Ensure that payload also contains an expiration
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expires})
    # Encode it to contain the signature
    encoded_jwt = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Refresh token is based on this article: 
# https://gh0stfrk.medium.com/token-based-authentication-with-fastapi-7d6a22a127bf
# It is created when the user logs in
def create_refresh_token(username: str, user_id: str, expires_delta: timedelta):
    payload = {
        "sub": username, 
        "_id": str(user_id)
    }
    expires = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": expires})
    refresh_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return refresh_jwt

# Used for checking if the refresh token is valid and then create new access token
def refresh_for_new_access_token(refresh_token: str):
    # We are currently not using blacklist
    # if refresh_token in blacklist:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Token has been revoked"
    #     )

    # Ensure there is a refresh token.
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token available"
        )
    try:
        # Decode signature to ensure it contains the username and id.
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("_id")
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        new_access_token = create_access_token(username, user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
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
# blacklist = set()

# This is used as our dependency for ensuring protected routes
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    # currently not using blacklist
    # if token in blacklist:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Token has been revoked"
    #     )
    try:
        # TODO: This is used several places, maybe we should create a function to follow DRY?
        # Or maybe it does not make sense?
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

# Helper function to check is token is expired
def decode_for_exp(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = int(payload.get("exp"))
    if exp < datetime.now(timezone.utc).timestamp():
        raise JWTError("Token expired")
    return {"username": payload.get("sub"), "_id": payload.get("_id")}

# I gave up, this is inspired by an approach suggested by ChatGPT. It works so I
# will leave it for now, but if we have time I would like to see if there is a way to
# make the approach cleaner. 
# I have tried to remove some logic into helper functions, to follow DRY
# The purpose is that it is used for protected routes, it checks the access token is not expired
# if it is we refresh it with the refresh token.
async def get_current_user_with_refresh(
    response: Response,
    access_token: Optional[str] = Cookie(None),
    refresh_token: Optional[str] = Cookie(None)
):
    if not access_token or not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access or refresh token"
        )
    try:
        decode_for_exp(access_token)
    except JWTError:
        # Try to refresh the access token using the refresh token if there is a JWTError
        # from the access token
        try:
            decode_for_exp(refresh_token)
            token_data = refresh_for_new_access_token(refresh_token)
            new_access_token = token_data["access_token"]

            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=False, 
                samesite="lax",
            )
            payload = jwt.decode(new_access_token, SECRET_KEY, algorithms=[ALGORITHM])
            return {"username": payload.get("sub"), "_id": payload.get("_id")}
        except Exception or JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No available refresh token for refresh"
            )