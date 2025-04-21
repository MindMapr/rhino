from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from datetime import datetime, timezone

# Routers
from .routes.user import router as user_v1
from .routes.time_frame import router as time_frame_v1
from .routes.task import router as task_v1

app = FastAPI(
    title="🦏 Rhino Service",
    description="Handles all interactions from frontend", # update description if relevant
    version="0.0.1"
)

# Used for CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000", # Next.js default localhost
]

# Include CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

# Had some issues with the errors from not being properly printed in backend, causing issues with troubleshooting. Found this exception handler. Since it is located in the main it handles all incoming excepts of type 422.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    for error in errors:
        if 'input' in error and isinstance(error['input'], bytes):
            error['input'] = error['input'].decode("utf-8")
    print("Validation error:", exc.errors())  # For debugging/logging purposes
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# TODO: This is used for testing and should be deleted before prod.
# It is used to check exp time on a decoded jwt token to confirm authentication behavior
exp = 1745004606
expiration_time = datetime.fromtimestamp(exp, timezone.utc)
print(expiration_time)

# Used for sending the HTTPExecptions as a header so we can use it as error responses in frontend
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    response = await http_exception_handler(request, exc)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000" # Ensure this matches frontend to avoid a CORS error
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# include routers
app.include_router(user_v1, prefix="/v1")
app.include_router(time_frame_v1, prefix="/v1")
app.include_router(task_v1, prefix="/v1")


@app.get("/")
async def root():
    print("Successful backend connection")
    return {"message": "Hello World"}

# Test the connection to the database
@app.get("/test-connection", tags=["Test Connection"])
async def test_connection():
    try:
        client = MongoClient()  # Create a MongoClient instance
        client.server_info()  # Test the connection
        return {"message": "Connection successful"}
    except Exception as e:
        return {"message": f"Connection failed: {str(e)}"}