from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class StatusResponse(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    docs: str


class FeedItemResponse(BaseModel):
    recipe_id: int
    title: str
    category: Optional[str] = None
    trust_score: float
    review_count: int
    trusted_reviewers: list[str]
    is_canonical: bool


class RecipeDetailResponse(BaseModel):
    recipe_id: int
    title: str
    category: Optional[str] = None
    ingredients: list[str]
    instructions: list[str]
    is_canonical: bool


class ReviewRequest(BaseModel):
    recipe_id: int
    raw_score: float = Field(..., ge=0.0, le=10.0)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    review_id: int
    z_score: float


class IngestRequest(BaseModel):
    title: str
    ingredients: list[str]
    category: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Title cannot be empty")
        return stripped


class IngestResponse(BaseModel):
    status: Literal["created", "duplicate_detected"]
    canonical_id: int
    confidence: float
    message: Optional[str] = None


class UserResponse(BaseModel):
    user_id: int
    username: str
    trust_authority: float


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1)
    email: Optional[str] = None
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def username_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Username cannot be empty")
        return stripped

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class FollowRequest(BaseModel):
    followee_id: int


class CookbookRequest(BaseModel):
    recipe_id: int


class CookbookRankingItem(BaseModel):
    recipe_id: int
    personal_rank: int
    z_score: float


class CookbookResponse(BaseModel):
    user_rankings: list[CookbookRankingItem]


class CookbookRankingUpdateItem(BaseModel):
    recipe_id: int
    personal_rank: int = Field(..., ge=1)


class CookbookRankingsRequest(BaseModel):
    rankings: list[CookbookRankingUpdateItem] = Field(..., min_length=1)


class TrustedContribution(BaseModel):
    username: str
    raw_score: float
    z_score: float
    trust_weight: float
    weighted_contribution: float


class TrustBreakdownResponse(BaseModel):
    recipe_id: int
    title: str
    trust_score: float
    review_count: int
    global_average_raw_score: Optional[float] = None
    trusted_contributions: list[TrustedContribution]
    non_trusted_review_count: int


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

    @field_validator("username")
    @classmethod
    def username_not_blank(cls, value: str) -> str:
        return value.strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
