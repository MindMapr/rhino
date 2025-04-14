from datetime import datetime, date
from fastapi import HTTPException, status
from uuid import UUID
from typing import List

from ..models.time_frame import TimeFrame, UpdateTimeFrame

# Constants
not_found_404 = "Time Frame not found"

class TimeFrameList():
    def __init__(self, db):
        self.db = db

    # Get all time frames in database
    def get_all_time_frames(self) -> List[TimeFrame]:
        result = self.db.find()
        number_of_time_frames = self.db.count_documents({})

        return {
            "status": status.HTTP_200_OK,
            "meta": number_of_time_frames,
            "data": [TimeFrame(**time_frame) for time_frame in result]
        }
    
    # Get a specific time frame from the database
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
        
    # Get all time frames for a specific user
    def get_all_user_specific_time_frames(self, user_id: str) -> List[TimeFrame]:
        result = self.db.find({"user_id": UUID(user_id)})

        return {
            "status": status.HTTP_200_OK,
            "data": [TimeFrame(**time_frame) for time_frame in result]
        }
    
    # Used to find the current active time frame that the user has
    def get_active_time_frame(self, user_id: str):
        result = self.db.find_one({
            "user_id": UUID(user_id),
            # $gte is a mongodb operator that works for comparision. It only find documents that are greater than or equal to the given value. In this case it only find the current active time frame document.
            "end_date": {"$gte": datetime.today()}
        })
        
        if result:
            return {
                "status": status.HTTP_200_OK,
                "data": TimeFrame(**result)
            }
        # We should probably have a check if there is more than two and then discuss the logic if that happens
        else:
            raise HTTPException (
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404 
            )


        
    def create_time_frame(self, time_frame: TimeFrame):
        if time_frame.start_date > time_frame.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date cannot be before start date."
            )
        print(time_frame)
        

        _ = self.db.insert_one(time_frame.model_dump(by_alias=True))

    def update_time_frame(self, time_frame_id: str, time_frame: UpdateTimeFrame):
        update_field = time_frame.model_dump(exclude_unset=True)

        result = self.db.update_one(
                {"_id": UUID(time_frame_id)},
                {"$set": update_field}
            )
        if result.modified_count:
            return {
                "status": status.HTTP_200_OK,
                "data": {"time_frame": str(result)}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_404
            )

    def delete_time_frame(self, time_frame_id: str):
        # should we do a check if the time_frame they are deleting has a match on their own id?
        result = self.db.delete_one({"_id": UUID(time_frame_id)})
        if result.deleted_count:
            return {
                "status": status.HTTP_200_OK,
                "data": {"time_frame": str(result)}
            }
        else:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = not_found_404
            )
