# DocNexus-AI

## Information retrieval (Member 3)

The backend indexes page-aware processed text with the
`sentence-transformers/all-MiniLM-L6-v2` model. MongoDB remains the source of
application and authorization records; the shared `docnexus_chunks` ChromaDB
collection stores chunk vectors and source metadata under `storage/chroma/`;
and `rank-bm25` provides lexical retrieval over the same authorized chunks.

`POST /documents/{document_id}/index`,
`GET /documents/{document_id}/index-status`, and
`DELETE /documents/{document_id}/index` manage the index. Authenticated search
uses `POST /retrieval/search` with `semantic`, `bm25`, or `hybrid` mode. Hybrid
ranking min-max normalizes each retriever's candidate scores and applies the
configured formula `0.6 * semantic + 0.4 * BM25` before deterministic sorting.

The embedding model is downloaded automatically on first use. Retrieval
evaluation templates and instructions are in `data/evaluation/`; no benchmark
score is claimed until relevance labels are supplied manually.

## Grounded answers (Member 4)

The backend uses the official `google-genai` SDK through a reusable provider
service. Configure `GEMINI_API_KEY` and `GEMINI_MODEL` in the ignored
`backend/.env`; never commit the key. `POST /answers/query` retrieves authorized
evidence through Member 3, assigns request-local source IDs, asks Gemini for an
evidence-only structured draft, validates citations against server-controlled
metadata, verifies claim support, and permits at most one repair attempt.

Retrieved document text is treated as untrusted data and clearly delimited from
instructions. If evidence is absent or inadequate, the API abstains instead of
using general model knowledge. Normal tests mock Gemini and do not make paid API
calls. A live smoke test is optional and should use only a non-sensitive,
processed and indexed development document.
