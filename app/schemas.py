from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

OttStatus = Literal["available", "announced", "unknown"]
AvailabilityType = Literal["stream", "rent", "buy"]


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class PlatformOut(BaseModel):
    id: int
    name: str
    slug: str
    logo_url: Optional[str] = None

    model_config = {"from_attributes": True}


class AvailabilityIn(BaseModel):
    platform_id: int
    availability_type: AvailabilityType = "stream"
    region: str = "IN"
    available_from: Optional[date] = None


class AvailabilityOut(BaseModel):
    id: int
    platform: PlatformOut
    availability_type: str
    region: str
    available_from: Optional[date] = None

    model_config = {"from_attributes": True}


class OttOut(BaseModel):
    status: str
    announced_date: Optional[date] = None
    predicted_date: Optional[date] = None
    predicted_window_days: Optional[int] = None
    confidence: Optional[float] = None
    model_version: Optional[str] = None

    model_config = {"from_attributes": True}


class MovieWrite(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    theatrical_date: Optional[date] = None
    language: str = "en"
    country: str = "IN"
    tmdb_id: Optional[int] = None
    ott_status: OttStatus = "unknown"
    announced_date: Optional[date] = None
    availability: list[AvailabilityIn] = Field(default_factory=list)


class MovieOut(BaseModel):
    id: int
    title: str
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    theatrical_date: Optional[date] = None
    language: str
    country: str
    tmdb_id: Optional[int] = None
    ott: Optional[OttOut] = None
    availability: list[AvailabilityOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class MovieListResponse(BaseModel):
    items: list[MovieOut]
    total: int
