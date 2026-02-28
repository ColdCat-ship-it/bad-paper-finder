import random

from app.database import get_collection, get_model

class PaperRepository:
    def __init__(self, collection=None, model=None):
        self.collection = collection or get_collection()
        self.model = model or get_model()

    def create(self, paper):
        emb = self.model.encode(paper.abstract)
        metadata = {
            "title": paper.title,
            "conference": paper.conference,
        }
        if paper.keywords:
            metadata["keywords"] = paper.keywords
        self.collection.add(
            ids=[paper.id],
            embeddings=[emb],
            documents=[paper.abstract],
            metadatas=[metadata],
        )

    def get_random(self):
        res = self.collection.get(include=["ids"])
        ids = res.get("ids") or []
        if not ids:
            return None
        random_id = random.choice(ids)
        return self.get_by_id(random_id)

    def conference_exists(self, conference_name: str) -> bool:
        target = self._normalize_conference(conference_name)
        if not target:
            return False
        res = self.collection.get(include=["metadatas"])
        for meta in res.get("metadatas", []):
            conf = (meta or {}).get("conference") or (meta or {}).get("conf") or ""
            if self._normalize_conference(conf) == target:
                return True
        return False

    def get_by_id(self, paper_id):
        res = self.collection.get(ids=[paper_id], include=["ids", "documents", "metadatas"])
        if not res.get("ids"):
            return None
        return self._build_paper(res["ids"][0], res["documents"][0], res["metadatas"][0])

    def get_all(self, limit=None):
        res = self.collection.get(include=["documents", "metadatas", "ids"])
        papers = [
            self._build_paper(res["ids"][i], res["documents"][i], res["metadatas"][i])
            for i in range(len(res["ids"]))
        ]
        if limit is not None:
            return papers[:limit]
        return papers

    def semantic_search(self, query: str, limit: int = 3):
        query_emb = self.model.encode(query)
        res = self.collection.query(query_embeddings=[query_emb], n_results=limit)
        papers = []
        for i in range(len(res["ids"][0])):
            paper = self._build_paper(
                res["ids"][0][i],
                res["documents"][0][i],
                res["metadatas"][0][i],
            )
            distances = res.get("distances")
            if distances:
                paper["relevance_score"] = 1 - distances[0][i]
            papers.append(paper)
        return papers

    def search_by_keywords(self, keywords, limit: int = 10):
        keywords_norm = [k.strip().lower() for k in keywords if k and k.strip()]
        if not keywords_norm:
            return []
        res = self.collection.get(include=["documents", "metadatas", "ids"])
        matches = []
        for i in range(len(res["ids"])):
            meta = res["metadatas"][i] or {}
            doc = res["documents"][i] or ""
            meta_keywords = meta.get("keywords") or []
            if isinstance(meta_keywords, str):
                meta_keywords = [k.strip() for k in meta_keywords.split(";") if k.strip()]
            haystack = " ".join(
                [
                    meta.get("title", ""),
                    doc,
                    " ".join(meta_keywords),
                ]
            ).lower()
            if any(k in haystack for k in keywords_norm):
                matches.append(self._build_paper(res["ids"][i], doc, meta))
            if len(matches) >= limit:
                break
        return matches

    def delete_by_ids(self, ids):
        if not ids:
            return 0
        existing = self.collection.get(ids=ids)
        if not existing.get("ids"):
            return 0
        self.collection.delete(ids=existing["ids"])
        return len(existing["ids"])

    def delete_by_titles(self, titles):
        if not titles:
            return 0
        titles_norm = {t.strip().lower() for t in titles if t and t.strip()}
        if not titles_norm:
            return 0
        res = self.collection.get(include=["metadatas", "ids"])
        ids_to_delete = []
        for i in range(len(res["ids"])):
            meta = res["metadatas"][i] or {}
            title = (meta.get("title") or "").strip().lower()
            if title and title in titles_norm:
                ids_to_delete.append(res["ids"][i])
        if not ids_to_delete:
            return 0
        self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

    def _build_paper(self, paper_id, document, metadata):
        meta = metadata or {}
        keywords = meta.get("keywords")
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(";") if k.strip()]
        return {
            "id": paper_id,
            "title": meta.get("title", ""),
            "abstract": document or meta.get("abstract", ""),
            "conference": meta.get("conference") or meta.get("conf") or "",
            "keywords": keywords,
            "rating": meta.get("rating"),
            "roast": meta.get("roast"),
        }

    @staticmethod
    def _normalize_conference(value: str) -> str:
        if not value:
            return ""
        return "".join(value.split()).lower()
