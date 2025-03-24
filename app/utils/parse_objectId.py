from bson.objectid import ObjectId as BsonObjectId

# FastAPI does not recognize MongoDBs ObjectId. This creates a custom type 
# so Pydantic is able to understand and validate the MongoDB ObjectID

# Based on stackoverflow article: https://stackoverflow.com/questions/59503461/how-to-parse-objectid-in-a-pydantic-model
class PydanticObjectId(BsonObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not BsonObjectId.is_valid(v):
            raise ValueError('ObjectId required')
        return BsonObjectId(v)