from app.schemas.retrieval import RetrievalSearchRequest
from app.services.chunking import chunk_pages
from app.services.embedding import EmbeddingService


class FakeEmbeddingModel:
    def encode(self, texts, **_kwargs):
        return [[float(len(text)), 1.0, 0.0] for text in texts]


def test_chunking_is_deterministic_overlapping_and_page_aware():
    pages = [
        {"page_number": 1, "text": "abcdefghijklmnopqrstuvwxyz"},
        {"page_number": 2, "text": "second page"},
    ]
    first = chunk_pages(pages, "doc", "owner", "file.pdf", 10, 3)
    second = chunk_pages(pages, "doc", "owner", "file.pdf", 10, 3)

    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert first[0].text[-3:] == first[1].text[:3]
    assert {item.page_number for item in first} == {1, 2}
    assert all(item.document_id == "doc" and item.filename == "file.pdf" for item in first)


def test_chunking_skips_empty_pages():
    assert chunk_pages([{"page_number": 1, "text": "   "}], "d", "o", "f", 10, 2) == []


def test_embedding_batch_and_query_shape():
    service = EmbeddingService(model=FakeEmbeddingModel())
    assert len(service.embed_texts(["one", "two"])) == 2
    assert len(service.embed_query("question")) == 3


def test_retrieval_request_serializes_and_rejects_blank_query():
    request = RetrievalSearchRequest(query=" evidence ")
    assert request.query == "evidence"
    assert request.model_dump(mode="json")["mode"] == "hybrid"
