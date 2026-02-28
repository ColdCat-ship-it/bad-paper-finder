from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import chromadb
from typing import List
from pathlib import Path
import json

app = FastAPI(title="Anti-ArXiv API", description="Find out why your research idea is actually terrible.")

# 1. Initialize the "Brain" (Local Embedding Model)
# This model is small, fast, and perfect for a hackathon.
model = SentenceTransformer('all-MiniLM-L6-v2')

# 2. Setup Vector Database (In-Memory for the Hackathon)
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="rejected_papers")


# 3. Data Model
class RejectedPaper(BaseModel):
    id: str
    title: str
    discipline: str
    fatal_flaw: str
    abstract_snippet: str
    reason_for_rejection: str


# 4. Data (from data.json in the project root)
def load_data() -> List[dict]:
    data_path = Path(__file__).resolve().parent / "data.json"
    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


# Seed the database on startup
@app.on_event("startup")
def seed_db():
    for item in load_data():
        # Turn the abstract snippet into a vector
        embedding = model.encode(item["abstract_snippet"]).tolist()
        collection.add(
            ids=[item["id"]],
            embeddings=[embedding],
            metadatas=[{"title": item["title"], "reason": item["reason_for_rejection"], "conf": item["discipline"]}],
            documents=[item["abstract_snippet"]]
        )


# 5. The Search Endpoint
@app.get("/search", response_model=List[dict])
async def search_rejections(query: str = Query(..., examples="I want to use crypto for AI")):
    # Convert user query to vector
    query_vec = model.encode(query).tolist()

    # Query the database
    results = collection.query(
        query_embeddings=[query_vec],
        n_results=2
    )

    # Format for the UI
    output = []
    for i in range(len(results['ids'][0])):
        output.append({
            "idea": results['documents'][0][i],
            "why_it_failed": results['metadatas'][0][i]['reason'],
            "original_title": results['metadatas'][0][i]['title'],
            "source": results['metadatas'][0][i]['conf']
        })
    return output


# 6. Root UI
@app.get("/", response_class=HTMLResponse)
async def root_ui():
    return """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>The Bad Paper Search</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; }
      form { max-width: 720px; }
      textarea { width: 100%; min-height: 120px; padding: 0.75rem; font-size: 1rem; }
      button { margin-top: 0.75rem; padding: 0.6rem 1rem; font-size: 1rem; }
      .hint { color: #666; font-size: 0.9rem; }
    </style>
  </head>
  <body>
    <h1>The Bad Paper Search</h1>
    <p class="hint">Type your research idea and submit to see why it might fail.</p>
    <form action="/search" method="get">
      <textarea name="query" placeholder="Machine Learning, Artificial Intelligence, AI4Science, AI infra"></textarea>
      <br />
      <button type="submit">Search</button>
    </form>
  </body>
</html>
"""
