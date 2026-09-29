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
