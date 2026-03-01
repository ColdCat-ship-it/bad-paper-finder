from fastapi import APIRouter, HTTPException, status, Query
from typing import List
from app.models import PaperRead, PaperCreate, PaperUpdate, PaperKeywordSearch, PaperDeleteRequest
from app.repository import PaperRepository

router = APIRouter()

# Initialize the repository with our database collection
# In a real app, you might use Dependency Injection here
repo = PaperRepository()


@router.get("/papers", response_model=List[PaperRead])
async def list_papers(limit: int = Query(1, ge=1, le=1)):
    """ Feeling lucky today?

    Use this function to GET a random paper.
    """
    paper = repo.get_random()
    if not paper:
        return []
    return [paper]

@router.get("/full/papers", response_model=List[PaperRead])
async def list_all_papers():
    """Get all rejected papers currently in the database."""
    return repo.get_all()

@router.get("/papers/list", response_model=List[PaperRead])
async def list_papers_by_count(limit: int = Query(10, ge=1, le=100, description="Number of papers to return, default to 10")):
    """List a number of papers (alias endpoint).
    """
    return repo.get_all(limit=limit)

@router.post("/papers", response_model=PaperRead, status_code=status.HTTP_201_CREATED)
async def create_paper(paper: PaperCreate):
    """Submit a new failed research idea."""
    # Check if ID already exists to keep it clean
    if repo.get_by_id(paper.id):
        raise HTTPException(status_code=400, detail="Paper ID already exists")
    if repo.conference_exists(paper.conference):
        raise HTTPException(
            status_code=400,
            detail="Conference already exists (case/whitespace-insensitive).",
        )

    repo.create(paper)
    return paper


@router.put("/papers/{paper_id}", response_model=PaperRead)
async def update_paper(paper_id: str, payload: PaperUpdate):
    """Partially update a paper by id (id is immutable)."""
    existing = repo.get_by_id(paper_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Paper not found")

    updates = payload.dict(exclude_unset=True)
    if "conference" in updates and updates["conference"] is not None:
        new_conf = repo._normalize_conference(updates["conference"])
        old_conf = repo._normalize_conference(existing.get("conference"))
        if new_conf and new_conf != old_conf and repo.conference_exists(updates["conference"]):
            raise HTTPException(
                status_code=400,
                detail="Conference already exists (case/whitespace-insensitive).",
            )

    updated = repo.update_by_id(paper_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Paper not found")
    return updated


@router.get("/papers/search", response_model=List[PaperRead])
async def search_papers(interest: str = Query(..., min_length=3), limit: int = Query(3, ge=1, le=100)):
    """
    The 'Magic' endpoint: Uses semantic search to find
    the most relevant rejected papers based on your interest.
    """
    results = repo.semantic_search(interest, limit=limit)
    if not results:
        raise HTTPException(status_code=404, detail="No similar bad ideas found. Yours might actually be original!")
    return results

@router.get("/papers/{paper_id}", response_model=PaperRead)
async def get_paper_by_id(paper_id: str):
    """Get a paper by id."""
    paper = repo.get_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


# @router.post("/papers/search/keywords", response_model=List[PaperRead])
# async def search_papers_by_keywords(payload: PaperKeywordSearch):
#     """Search by keywords across title, abstract, and stored keywords."""
#     results = repo.search_by_keywords(payload.keywords, limit=payload.limit)
#     if not results:
#         raise HTTPException(status_code=404, detail="No keyword matches found.")
#     return results


@router.delete("/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(paper_id: str):
    """Remove a paper from the database by id."""
    deleted = repo.delete_by_ids([paper_id])
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Paper not found")
    return None


@router.delete("/papers", status_code=status.HTTP_204_NO_CONTENT)
async def delete_papers(payload: PaperDeleteRequest):
    """Remove papers from the database by ids and/or titles."""
    if not payload.ids and not payload.titles:
        raise HTTPException(status_code=400, detail="Provide ids and/or titles to delete.")
    deleted = 0
    if payload.ids:
        deleted += repo.delete_by_ids(payload.ids)
    if payload.titles:
        deleted += repo.delete_by_titles(payload.titles)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="No matching papers found to delete.")
    return None
