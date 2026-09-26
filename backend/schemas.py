from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = None



class ChatResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime
    sources: Optional[List[dict]] = []

    class Config:
        from_attributes = True
