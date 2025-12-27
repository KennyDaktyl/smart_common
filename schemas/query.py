from pydantic import BaseModel, Field
from typing import Optional


class PaginationQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    search: Optional[str] = Field(default=None, description="Full-text like search")
