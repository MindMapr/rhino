import os
from zoneinfo import ZoneInfo
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

# Loading the connection variable from .env file
load_dotenv()

# Connect to the database
atlas_uri = os.getenv("DB_URI")
client = MongoClient(atlas_uri, tlsCAFile=certifi.where(), uuidRepresentation='standard', tz_aware=True)
database = client.db