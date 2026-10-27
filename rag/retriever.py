import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import chromadb

from rag.embeddings import embed_texts
from rag.ranking import rank_and_filter

load_dotenv()

CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "heydocai-medkb")


def retrieve_top_k(
    query: str,
    top_k: int = 12,              # fetch more initially
    min_score: float = 0.50,      # filter after retrieval
    final_top_k: int = 6,         # return fewer, higher-signal
) -> List[Dict[str, Any]]:
    if not query.strip():
        return []

    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    query_embedding = embed_texts([query])[0]

    res = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = res.get("documents", [[]])[0] if res.get("documents") else []
    metas = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
    dists = res.get("distances", [[]])[0] if res.get("distances") else []

    raw_results = []
    for doc, meta, dist in zip(docs, metas, dists):
        # Chroma returns cosine DISTANCE (lower = more similar).
        # Convert to a similarity score in the same "higher = better" direction
        # that ranking.py / guards.py expect (mirrors old Pinecone score usage).
        score = 1.0 - float(dist)
        raw_results.append({
            "text": doc,
            "score": score,
            "metadata": meta or {},
        })

    return rank_and_filter(
        raw_results,
        min_score=min_score,
        final_top_k=final_top_k,
        max_context_chars=4500,
        per_chunk_char_cap=900,
    )