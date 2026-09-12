from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OnboardingIn(BaseModel):
    name: str = Field(min_length=1)
    phone: str | None = None
    tags: list[str] = []
    lat: float | None = None
    lng: float | None = None


class ProfilePatch(BaseModel):
    name: str | None = None
    phone: str | None = None
    tags: list[str] | None = None
    lat: float | None = None
    lng: float | None = None
    default_radius_mi: float | None = Field(default=None, ge=0.5, le=50)


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    lat: float
    lng: float
    address: str = ""
    city: str = "Pittsburgh"
    starts_at: datetime
    ends_at: datetime
    people_min: int = Field(default=2, ge=1)
    people_max: int = Field(default=20, ge=1)
    cost_estimate: str = "Free"
    tags: list[str] = []
