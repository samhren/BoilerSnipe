from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
import re


# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    token: str


# Course Schemas
class CourseBase(BaseModel):
    crn: str
    course_code: str
    title: str
    instructor: Optional[str] = None
    time: Optional[str] = None
    days: Optional[str] = None
    schedule_type: Optional[str] = None
    term_code: str
    term_name: Optional[str] = None


class CourseResponse(CourseBase):
    id: int
    seats_available: int
    seats_capacity: int
    seats_remaining: int
    last_checked: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CourseSearch(BaseModel):
    query: str
    term_code: Optional[str] = None


# Track Schemas
class TrackCreate(BaseModel):
    crn: str  # User provides CRN to track
    notify_on_open: bool = True
    notify_on_close: bool = False


class TrackResponse(BaseModel):
    id: int
    user_id: int
    course: CourseResponse
    last_status: str
    last_seats: int
    last_notified: Optional[datetime]
    last_checked: Optional[datetime]
    notify_on_open: bool
    notify_on_close: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TrackUpdate(BaseModel):
    notify_on_open: Optional[bool] = None
    notify_on_close: Optional[bool] = None
    is_active: Optional[bool] = None


# Scraper Schemas
class ScraperConfig(BaseModel):
    term_code: str
    subjects: List[str]  # e.g., ["MA", "CS", "ECON"]
    course_numbers: Optional[List[str]] = None  # Optional specific courses


class SeatStatus(BaseModel):
    crn: str
    seats_remaining: int
    seats_capacity: int
    status: str  # "open" or "closed"
    last_checked: datetime
