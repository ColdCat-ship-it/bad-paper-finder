import json
import math
import re
import hashlib
from pathlib import Path

# Lightweight, dependency-free embedding + collection implementation.
# This replaces chromadb + sentence-transformers to keep the API self-contained.

class SimpleHashEmbedder:
    def __init__(self, dim: int = 512):
        self.dim = dim

    def encode(self, text: str):
        text = text or ""
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        vec = [0.0] * self.dim
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def _cosine_sim(a, b):
    if not a or not b:
        return 0.0
    dot = 0.0
    for i in range(min(len(a), len(b))):
        dot += a[i] * b[i]
    return dot


class SimpleCollection:
    def __init__(self, name: str, model: SimpleHashEmbedder):
        self.name = name
        self.model = model
        self._ids = []
        self._docs = []
        self._metas = []
        self._embeddings = []

    def count(self):
        return len(self._ids)

    def add(self, ids, embeddings=None, documents=None, metadatas=None):
        documents = documents or [""] * len(ids)
        metadatas = metadatas or [None] * len(ids)
        if embeddings is None:
            embeddings = [self.model.encode(doc) for doc in documents]
        for i, pid in enumerate(ids):
            self._ids.append(pid)
            self._docs.append(documents[i])
            self._metas.append(metadatas[i])
            self._embeddings.append(embeddings[i])

    def get(self, ids=None, include=None):
        include = include or ["ids"]
        if ids is None:
            idxs = range(len(self._ids))
        else:
            id_set = set(ids)
            idxs = [i for i, pid in enumerate(self._ids) if pid in id_set]
        res = {}
        if "ids" in include:
            res["ids"] = [self._ids[i] for i in idxs]
        if "documents" in include:
            res["documents"] = [self._docs[i] for i in idxs]
        if "metadatas" in include:
            res["metadatas"] = [self._metas[i] for i in idxs]
        return res

    def delete(self, ids):
        if not ids:
            return
        id_set = set(ids)
        new_ids = []
        new_docs = []
        new_metas = []
        new_embeddings = []
        for i, pid in enumerate(self._ids):
            if pid in id_set:
                continue
            new_ids.append(pid)
            new_docs.append(self._docs[i])
            new_metas.append(self._metas[i])
            new_embeddings.append(self._embeddings[i])
        self._ids = new_ids
        self._docs = new_docs
        self._metas = new_metas
        self._embeddings = new_embeddings

    def query(self, query_embeddings, n_results=3):
        if not self._ids:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        q = query_embeddings[0] if query_embeddings else []
        if not q:
            q = self.model.encode("")
        scored = []
        for i in range(len(self._ids)):
            sim = _cosine_sim(q, self._embeddings[i])
            dist = 1 - sim
            scored.append((dist, i))
        scored.sort(key=lambda x: x[0])
        top = scored[:n_results]
        ids = [self._ids[i] for _, i in top]
        docs = [self._docs[i] for _, i in top]
        metas = [self._metas[i] for _, i in top]
        distances = [d for d, _ in top]
        return {"ids": [ids], "documents": [docs], "metadatas": [metas], "distances": [distances]}


# Shared instances
_model = SimpleHashEmbedder()
_collection = SimpleCollection("rejected_papers", _model)
_DATA_PATHS = [
    Path(__file__).resolve().parents[1] / "failed_iclr_more_db.json",
    # Path(__file__).resolve().parents[1] / "roasted_icml_db.json",
    Path(__file__).resolve().parents[1] / "roasted_nips_db.json",
]

def init_db():
    """Loads/merges JSON files into memory, skipping already-loaded ids."""
    existing = _collection.get(include=["ids"]) if _collection.count() > 0 else {"ids": []}
    seen_ids = set(existing.get("ids") or [])
    for path in _DATA_PATHS:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                paper_id = item.get("id")
                if not paper_id or paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)
                abstract = item.get("abstract") or item.get("abstract_snippet") or ""
                embedding = _model.encode(abstract)
                metadata = {
                    "title": item.get("title", ""),
                    "conference": item.get("conference") or item.get("conf") or item.get("track") or "",
                    "rating": item.get("rating"),
                    "roast": item.get("roast"),
                }
                keywords = item.get("keywords")
                if keywords:
                    if isinstance(keywords, str):
                        metadata["keywords"] = [k.strip() for k in keywords.split(";") if k.strip()]
                    else:
                        metadata["keywords"] = keywords
                _collection.add(
                    ids=[paper_id],
                    embeddings=[embedding],
                    documents=[abstract],
                    metadatas=[metadata],
                )

def get_collection():
    if _collection.count() == 0:
        init_db()
    return _collection
def get_model(): return _model
