from typing_extensions import Annotated
from pydantic.functional_validators import AfterValidator
from bson import ObjectId as BsonObjectId

# IMPORTANT: Currently not used as we migrated to UUID. Keeping it for now in case we find a solution to validation error with PyObjectID

# FastAPI does not recognize MongoDBs ObjectId. This creates a custom type 
# so Pydantic is able to understand and validate the MongoDB ObjectID

# Based on stackoverflow article: https://stackoverflow.com/questions/59503461/how-to-parse-objectid-in-a-pydantic-model
class PydanticObjectId(BsonObjectId):
    def check_object_id(value: str) -> str:
        if not BsonObjectId.is_valid(value):
            raise ValueError('Invalid ObjectId')
        return value


    BsonObjectId = Annotated[str, AfterValidator(check_object_id)]