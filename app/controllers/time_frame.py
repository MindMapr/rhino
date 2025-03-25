from fastapi import HTTPException, status
from uuid import UUID
from typing import List

from ..models.time_frame import TimeFrame

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
