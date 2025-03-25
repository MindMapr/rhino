from fastapi import HTTPException, status
from uuid import UUID
from typing import List

from ..models.time_frame import TimeFrame

# Constants
not_found_404 = "Time Frame not found"

class TimeFrameList():
    def __init__(self, db):
        self.db = db

    def get_all_time_frames(self) -> List[TimeFrame]:
        result = self.db.find()
        number_of_time_frames = self.db.count_documents({})

        return {
            "status": status.HTTP_200_OK,
            "meta": number_of_time_frames,
            "data": [TimeFrame(**time_frame) for time_frame in result]
        }
    
    def get_single_time_frame(self, time_frame_id: str):
        result = self.db.find_one({"_id": UUID(time_frame_id)})
        if result:
            return {
                "status": status.HTTP_200_OK,
                "data": TimeFrame(**result)
            }
        else:
            raise HTTPException (
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404 
            )
        
    def create_time_frame(self, time_frame: TimeFrame):
        _ = self.db.insert_one(time_frame.model_dump(by_alias=True))
