from app.schemas.retrieval import DocumentChunk, RetrievalResult
from app.services.bm25 import BM25Retriever
from app.services.hybrid_retrieval import combine_results
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


def test_bm25_search_and_empty_query(tmp_path):
    store = VectorStore(tmp_path, "bm25_chunks")
    store.upsert_chunks(
        [chunk("one", "termination notice clause"), chunk("two", "payment schedule", 1)],
        [[1.0, 0.0], [0.0, 1.0]],
    )
    retriever = BM25Retriever(store)
    assert retriever.search("termination", ["doc1"], 5)[0].chunk_id == "one"
    assert retriever.search("!!!", ["doc1"], 5) == []
    assert retriever.search("unmatched", ["doc1"], 5) == []


def result(chunk_id: str, index: int, semantic=None, bm25=None) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc",
        filename="file.pdf",
        page_number=1,
        chunk_index=index,
        text=chunk_id,
        semantic_score=semantic,
        bm25_score=bm25,
    )


def test_hybrid_normalizes_ranks_limits_and_breaks_ties_stably():
    semantic = [result("b", 1, semantic=0.8), result("a", 0, semantic=0.8)]
    bm25 = [result("a", 0, bm25=3.0), result("c", 2, bm25=1.0)]
    combined = combine_results(semantic, bm25, 2, 0.6, 0.4)

    assert len(combined) == 2
    assert combined[0].chunk_id == "a"
    assert all(0 <= (item.hybrid_score or 0) <= 1 for item in combined)


def test_hybrid_uses_stable_source_order_for_equal_scores():
    tied = [result("later", 2, semantic=0.5), result("earlier", 1, semantic=0.5)]
    combined = combine_results(tied, [], 5, 0.6, 0.4)
    assert [item.chunk_id for item in combined] == ["earlier", "later"]
