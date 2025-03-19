from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="🦏 Rhino Service",
    description="Handles all interactions from frontend", # update description if relevant
    version="0.0.1"
)

# Used for CORS
origins = [
    "http://localhost",
    "http://localhost:8000"
]

# Include CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)


@app.get("/")
async def root():
    return {"message": "Hello World"}
