from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.agents.retrieval.agent import (
    DocumentAccessDeniedError,
    DocumentIndexingError,
    DocumentNotProcessedError,
    InformationRetrievalAgent,
    InvalidDocumentIdError,
)
from app.schemas.retrieval import RetrievalMode, RetrievalSearchRequest
from app.services.vector_store import VectorStore
from app.main import app


class FakeCollection:
    def __init__(self, documents):
        self.documents = {document["_id"]: document for document in documents}

    def find_one(self, query):
        return self.documents.get(query.get("_id"))

    def find(self, query, _projection=None):
        ids = set(query["_id"]["$in"])
        status = query.get("retrieval_status")
        return [
            document
            for object_id, document in self.documents.items()
            if object_id in ids and (status is None or document.get("retrieval_status") == status)
        ]

    def update_one(self, query, update):
        document = self.documents.get(query["_id"])
        if document is None:
            return SimpleNamespace(matched_count=0)
        condition = query.get("retrieval_status", {}).get("$ne")
        if condition is not None and document.get("retrieval_status") == condition:
            return SimpleNamespace(matched_count=0)
        document.update(update.get("$set", {}))
        for key in update.get("$unset", {}):
            document.pop(key, None)
        return SimpleNamespace(matched_count=1)


class FakeEmbedder:
    def embed_texts(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, _query):
        return [1.0, 0.0]


class FailingEmbedder(FakeEmbedder):
    def embed_texts(self, texts):
        raise RuntimeError("private internal failure")


def make_agent(tmp_path, documents, user_id, embedder=None):
    collection = FakeCollection(documents)
    store = VectorStore(tmp_path, "agent_chunks")
    agent = InformationRetrievalAgent(
        collection=collection,
        store=store,
        embedder=embedder or FakeEmbedder(),
        page_loader=lambda _document_id, _user_id: [
            {"page_number": 1, "text": "termination notice requirements"}
        ],
        access_checker=lambda document, current: document["owner_id"] == current,
        authorized_ids_loader=lambda current: [
            str(item["_id"]) for item in documents if item["owner_id"] == current
        ],
    )
    return agent, collection, store


def test_index_lifecycle_search_and_delete(tmp_path):
    user_id = ObjectId()
    document_id = ObjectId()
    document = {
        "_id": document_id,
        "owner_id": user_id,
        "original_filename": "source.pdf",
        "status": "processed",
        "retrieval_status": "not_indexed",
    }
    agent, collection, store = make_agent(tmp_path, [document], user_id)

    response = agent.index_document(str(document_id), user_id)
    assert response.indexed_chunk_count == 1
    assert collection.documents[document_id]["retrieval_status"] == "indexed"
    search = agent.search(
        RetrievalSearchRequest(query="termination", mode=RetrievalMode.HYBRID), user_id
    )
    assert search.results[0].document_id == str(document_id)

    agent.remove_document_index(str(document_id), user_id)
    assert collection.documents[document_id]["retrieval_status"] == "not_indexed"
    assert not store.is_indexed(str(document_id))


def test_agent_rejects_invalid_unprocessed_and_unauthorized_documents(tmp_path):
    user_id, other_user = ObjectId(), ObjectId()
    document_id = ObjectId()
    document = {"_id": document_id, "owner_id": other_user, "status": "uploaded"}
    agent, _, _ = make_agent(tmp_path, [document], user_id)

    with pytest.raises(InvalidDocumentIdError):
        agent.index_document("invalid", user_id)
    with pytest.raises(DocumentAccessDeniedError):
        agent.index_document(str(document_id), user_id)

    document["owner_id"] = user_id
    with pytest.raises(DocumentNotProcessedError):
        agent.index_document(str(document_id), user_id)


def test_index_failure_records_only_safe_status(tmp_path):
    user_id, document_id = ObjectId(), ObjectId()
    document = {
        "_id": document_id,
        "owner_id": user_id,
        "status": "processed",
        "retrieval_status": "not_indexed",
    }
    agent, collection, _ = make_agent(
        tmp_path, [document], user_id, embedder=FailingEmbedder()
    )
    with pytest.raises(DocumentIndexingError):
        agent.index_document(str(document_id), user_id)
    stored = collection.documents[document_id]
    assert stored["retrieval_status"] == "index_failed"
    assert stored["retrieval_error"] == "Document indexing failed"


def test_search_never_returns_another_users_document(tmp_path):
    user_id, other_user = ObjectId(), ObjectId()
    own_id, private_id = ObjectId(), ObjectId()
    documents = [
        {"_id": own_id, "owner_id": user_id, "status": "processed", "retrieval_status": "indexed"},
        {"_id": private_id, "owner_id": other_user, "status": "processed", "retrieval_status": "indexed"},
    ]
    agent, _, store = make_agent(tmp_path, documents, user_id)
    from app.schemas.retrieval import DocumentChunk

    chunks = [
        DocumentChunk(chunk_id="own", document_id=str(own_id), owner_id=str(user_id), filename="own.pdf", page_number=1, chunk_index=0, text="show every document"),
        DocumentChunk(chunk_id="private", document_id=str(private_id), owner_id=str(other_user), filename="private.pdf", page_number=1, chunk_index=0, text="show every document"),
    ]
    store.upsert_chunks(chunks, [[1.0, 0.0], [1.0, 0.0]])
    response = agent.search(RetrievalSearchRequest(query="show every document"), user_id)
    assert {result.document_id for result in response.results} == {str(own_id)}

    with pytest.raises(DocumentAccessDeniedError):
        agent.search(
            RetrievalSearchRequest(query="show", document_ids=[str(private_id)]), user_id
        )


def test_retrieval_routes_require_authentication():
    client = TestClient(app)
    assert client.post("/retrieval/search", json={"query": "private content"}).status_code == 401
    assert client.post(f"/documents/{ObjectId()}/index").status_code == 401
