# Retrieval evaluation

`retrieval_queries.json` is intentionally an empty labeling template; no relevance
ground truth has been invented. Each query entry should use this shape:

```json
{
  "query_id": "IR-001",
  "query": "a natural-language search query",
  "document_ids": ["optional authorized search scope"],
  "relevant_document_ids": ["manually verified MongoDB document IDs"],
  "notes": "why these documents are relevant"
}
```

From `backend/`, run the evaluator against an authenticated user's labeled corpus:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py ..\data\evaluation\retrieval_queries.json --user-id USER_OBJECT_ID --k 5
```

The runner reports measured Precision@K, Recall@K, and MRR for BM25,
semantic, and hybrid modes. It does not upload or process CUAD files.
