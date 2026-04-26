from pydantic import BaseModel, Field


class ActorSchema(BaseModel):
    user_id: str
    display_name: str


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1)
