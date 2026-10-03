from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    question: str
    subject: Optional[str] = "General"
    history: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    id: int
    subject: Optional[str] = "General"
    question: str
    answer: str
    created_at: datetime
    sources: Optional[List[dict]] = []

    class Config:
        from_attributes = True



class UserProfileRequest(BaseModel):
    name: Optional[str] = "Rajesh Gouda"
    usn: Optional[str] = "4DM24AI038"
    semester: str
    branch: str
    branch_full: Optional[str] = None
    subjects: List[dict]


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    usn: str
    semester: str
    branch: str
    branch_full: Optional[str] = None
    subjects: List[dict]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

