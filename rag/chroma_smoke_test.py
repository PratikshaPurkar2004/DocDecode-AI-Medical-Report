import os
from dotenv import load_dotenv
import chromadb


def main():
    load_dotenv()

    db_dir = os.getenv("CHROMA_DB_DIR", "chroma_db")
    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "heydocai-medkb")

    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Connected to local Chroma collection: '{collection_name}' (dir: {db_dir})")

    # text-embedding-004 -> 768 dims
    test_vector = [0.001] + [0.0] * 767

    collection.upsert(
        ids=["smoke-test-1"],
        embeddings=[test_vector],
        metadatas=[{"source": "smoke_test", "text": "hello chroma"}],
        documents=["hello chroma"],
    )

    res = collection.query(
        query_embeddings=[test_vector],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    if res.get("ids") and res["ids"][0]:
        print("Query returned a match:")
        print(res)
    else:
        raise RuntimeError("Query returned no matches. Something is wrong.")

    print("Chroma smoke test PASSED.")


if __name__ == "__main__":
    main()