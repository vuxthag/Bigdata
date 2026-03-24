from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, UserUpdate
from app.schemas.cv import CVResponse, CVListResponse
from app.schemas.job import JobCreate, JobResponse, JobListResponse
from app.schemas.recommendation import (
    RecommendByTitleRequest,
    RecommendByCVRequest,
    RecommendedJob,
    RecommendResponse,
    InteractionCreate,
)

__all__ = [
    "UserCreate", "UserLogin", "UserResponse", "TokenResponse", "UserUpdate",
    "CVResponse", "CVListResponse",
    "JobCreate", "JobResponse", "JobListResponse",
    "RecommendByTitleRequest", "RecommendByCVRequest",
    "RecommendedJob", "RecommendResponse", "InteractionCreate",
]
