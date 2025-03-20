from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

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

# Test the connection to the database
@app.get("/test-connection", tags=["Test Connection"])
async def test_connection():
    try:
        client = MongoClient()  # Create a MongoClient instance
        client.server_info()  # Test the connection
        return {"message": "Connection successful"}
    except Exception as e:
        return {"message": f"Connection failed: {str(e)}"}