from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserLogin(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    role: str

    class Config:
        orm_mode = True


class DataItemBase(BaseModel):
    external_id: str
    source: str
    text: str
    extra_data: Optional[Dict[str, Any]] = {}


class DataItemCreate(DataItemBase):
    pass


class DataItemResponse(DataItemBase):
    id: int
    dataset_id: int
    assigned_to: Optional[int] = None

    class Config:
        orm_mode = True


class DataItemWithAnnotation(DataItemResponse):
    annotation: Optional["AnnotationResponse"] = None


class AnnotationCreate(BaseModel):
    label: bool


class AnnotationUpdate(BaseModel):
    label: bool


class AnnotationResponse(BaseModel):
    id: int
    data_item_id: int
    user_id: int
    label: bool
    reviewed: bool
    reviewed_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DatasetCreate(BaseModel):
    name: str
    items: List[DataItemCreate]


class DatasetResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    item_count: int = 0
    annotated_count: int = 0

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class ReviewRequest(BaseModel):
    annotation_id: int
    approved: bool