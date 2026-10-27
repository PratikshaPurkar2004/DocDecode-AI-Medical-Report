import os
import hashlib
from typing import List
from dotenv import load_dotenv
import chromadb

from rag.chunking import TextChunk
from rag.embeddings import embed_texts

load_dotenv()

CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "chroma_db")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "heydocai-medkb")


def _make_id(meta: dict) -> str:
    """
    Stable ID per chunk so re-runs don't duplicate vectors.
    """
    base = f"{meta.get('source')}|p{meta.get('page')}|c{meta.get('chunk_id')}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def get_collection():
    """
    Local, on-disk Chroma collection. No API key or account needed.
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=None,
    metadata={"hnsw:space": "cosine"},
)
    return collection


def upsert_chunks(chunks: List[TextChunk], batch_size: int = 64):
    collection = get_collection()

    total = len(chunks)
    print(f"Upserting {total} chunks into Chroma collection '{COLLECTION_NAME}' (dir: {CHROMA_DB_DIR})...")

    for start in range(0, total, batch_size):
        batch = chunks[start:start + batch_size]
        texts = [c.text for c in batch]
        vectors = embed_texts(texts)

        ids, metadatas, documents = [], [], []
        for c, vec in zip(batch, vectors):
            meta = dict(c.metadata)
            vec_id = _make_id(meta)

            ids.append(vec_id)
            metadatas.append(meta)
            documents.append(c.text)

        collection.upsert(
            ids=ids,
            embeddings=vectors,
            metadatas=metadatas,
            documents=documents,
        )
        print(f"{min(start + batch_size, total)}/{total} upserted")

    print("Upsert complete.")