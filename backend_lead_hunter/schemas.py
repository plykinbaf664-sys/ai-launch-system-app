from pydantic import BaseModel, Field


class HuntRequest(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    max_competitors: int = Field(default=10, ge=1, le=50)
    max_comments_per_post: int = Field(default=80, ge=1, le=500)


class HuntResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobState(BaseModel):
    status: str
    detail: str


class LeadResult(BaseModel):
    status: str
    analysis: str
    offer: str


class ViralPost(BaseModel):
    competitor_username: str
    competitor_full_name: str | None = None
    url: str
    caption: str
    comments_count: int


class HotLead(BaseModel):
    status: str = "HOT"
    username: str
    profile_url: str
    comment_text: str
    post_url: str
    competitor_username: str
    competitor_full_name: str | None = None
    analysis: str
    offer: str
