import datetime
from pydantic import BaseModel, EmailStr, validator


class GeoLocation(BaseModel):
    type: str = "Point"
    coordinates: tuple[float, float]


class PeriodicSchedule(BaseModel):
    start_date: datetime.date
    days: list[list[datetime.time]]

    @validator("days")
    def validate_days(cls, v):
        if len(v) != 0:
            raise ValueError("Days cannot be empty")
        return v


class User(BaseModel):
    name: str
    email: EmailStr
    phone: str


class RegisterRequest(User):
    password: str


class UserInDB(User):
    hashed_password: bytes
    salt: bytes
    reservation_ids: list[str] = []


class Guide(BaseModel):
    user_id: str
    languages: list[str]
    rating: float = None
    bio: str


class GuideRegisterRequest(Guide):
    password: str


class Tour(BaseModel):
    name: str
    description: str
    location: GeoLocation
    guide_id: str
    rating: float = None
    guide_salary: float
    duration: float
    dates: list[datetime.datetime] | PeriodicSchedule

    @validator("guide_salary")
    def validate_guide_salary(cls, v):
        if v < 0:
            raise ValueError("Guide salary cannot be negative")
        return v

    @validator("duration")
    def validate_duration(cls, v):
        if v < 0:
            raise ValueError("Duration cannot be negative")
        return v

    @validator("dates")
    def validate_dates(cls, v):
        if isinstance(v, list):
            for date in v:
                if date < datetime.datetime.now():
                    raise ValueError("Dates cannot be in the past")
        return v


class Reservation(BaseModel):
    date: datetime.datetime
    tour_id: str
    review_id: str


class ReservationInDB(Reservation):
    notified_participants: bool = False
    review_requests: list[datetime.datetime] = []


class Review(BaseModel):
    rating: float
    body: str
    author_id: str
    date: datetime.date
