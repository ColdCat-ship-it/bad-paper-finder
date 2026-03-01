from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import papers
from app.database import init_db

app = FastAPI(
    title="Find Quality Bad Paper API",
    description="A public API for the research ideas that didn't make the cut.",
    version="1.0.0"
)

# Allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 1. Initialize the Database/Collection on startup
@app.on_event("startup")
def startup_event():
    # This loads your data.json into ChromaDB/Memory
    init_db()

# 2. Include the Routers (Endpoint Modules)
# Using a prefix helps versioning (e.g., /v1/papers)
app.include_router(papers.router, prefix="/v1", tags=["Papers"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Find Quality Bad Paper API. Submit your bad ideas at /v1/papers."}
