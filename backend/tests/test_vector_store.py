import chromadb

from app.schemas.retrieval import DocumentChunk
from app.services.vector_store import VectorStore


def chunk(chunk_id: str, text: str, index: int = 0) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="doc1",
        owner_id="owner1",
        filename="source.pdf",
        page_number=1,
        chunk_index=index,
        text=text,
    )


def test_chroma_upsert_search_and_delete(tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path))
    store = VectorStore(tmp_path, "test_chunks", client)
    chunks = [chunk("one", "termination notice"), chunk("two", "payment terms", 1)]
    store.upsert_chunks(chunks, [[1.0, 0.0], [0.0, 1.0]])
    store.upsert_chunks(chunks, [[1.0, 0.0], [0.0, 1.0]])

    assert len(store.get_chunks(["doc1"])) == 2
    assert store.semantic_search([1.0, 0.0], ["doc1"], 1)[0].chunk_id == "one"
    store.delete_document("doc1")
    assert not store.is_indexed("doc1")
