from rag.loaders import load_knowledge_base
from rag.chunking import chunk_documents
from rag.chroma_upsert import upsert_chunks


def main():
    docs = load_knowledge_base("data/knowledge_base")
    chunks = chunk_documents(docs, chunk_size=1000, overlap=150)

    print(f"Pages loaded: {len(docs)}")
    print(f"Chunks created: {len(chunks)}")

    upsert_chunks(chunks, batch_size=64)


if __name__ == "__main__":
    main()