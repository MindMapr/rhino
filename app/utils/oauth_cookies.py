from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2
from typing import Optional

# Inspiration from here: https://github.com/fastapi/fastapi/issues/796
# Class used to keep OAuth2 which is useful for testing in Fastapi docs
# while still storing the token in a cookie for security measures.
# We get the access token from cookie instead of header.
class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str, # This is the url from oauth2_scheme in the auth.py
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        
        # flows is for telling OAuth2 that we are using the password flow with our tokenUrl
        flows = {"password": {"tokenUrl": tokenUrl}}
        # super is to call parent construct OAuth2 and ensuring it receives the attributes it expects
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    # __call__ ensures we can create a dependency for our protected endpoints using our access token cookie
    async def __call__(self, request: Request) -> Optional[str]:
        # Look for the access token in cookies.
        token = request.cookies.get("access_token")
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return token
