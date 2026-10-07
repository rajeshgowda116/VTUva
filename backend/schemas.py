from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    question: str
    subject: Optional[str] = "General"
    subject_code: Optional[str] = None
    semester: Optional[str] = None
    module: Optional[int] = None
    debug: Optional[bool] = False
    history: Optional[List[dict]] = None


class ChatResponse(BaseModel):
    id: int
    subject: Optional[str] = "General"
    question: str
    answer: str
    created_at: datetime
    sources: Optional[List[dict]] = []
    debug_info: Optional[dict] = None

    class Config:
        from_attributes = True


class UserRegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    usn: Optional[str] = "4DM24AI038"
    semester: Optional[str] = "5th Semester"
    branch: Optional[str] = "AIML"


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserAuthResponse(BaseModel):
    id: int
    email: str
    name: str
    usn: str
    semester: str
    branch: str
    token: str

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


class VTUUpdateResponse(BaseModel):
    id: int
    category: str
    title: str
    summary: str
    time_posted: str
    badge_color: str
    icon_type: str
    link: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PYQQuestionGroupResponse(BaseModel):
    id: int
    subject_code: str
    module: int
    canonical_question: str
    repetition_count: int
    years_asked: str
    importance_tier: str

    class Config:
        from_attributes = True


class PYQQuestionResponse(BaseModel):
    id: int
    question_id: str
    subject_code: str
    subject_name: Optional[str]
    year: int
    session: Optional[str]
    module: int
    main_question: Optional[str]
    sub_question: Optional[str]
    question_text: str
    marks: Optional[int]
    blooms_level: Optional[str]
    course_outcome: Optional[str]
    group_id: Optional[int]

    class Config:
        from_attributes = True



