from pydantic import BaseModel, Field
from typing import Optional, List
from typing import Any, Dict

# What the user sends to create a paper
class PaperCreate(BaseModel):
    id: str
    title: str = Field(..., min_length=3)
    abstract: str = Field(..., min_length=3)
    conference: str
    keywords: Optional[List[str]] = None

# What the API returns (includes similarity score for search)
class PaperRead(PaperCreate):
    relevance_score: Optional[float] = None
    rating: Optional[str] = None
    roast: Optional[Dict[str, Any]] = None

# Keyword search input
class PaperKeywordSearch(BaseModel):
    keywords: List[str] = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=100)

# Delete by ids and/or titles
class PaperDeleteRequest(BaseModel):
    ids: Optional[List[str]] = None
    titles: Optional[List[str]] = None
