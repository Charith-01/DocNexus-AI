# Grounded answer evaluation

`answer_verification_cases.json` is intentionally empty until a reviewer labels
real, authorized DocNexus documents. A completed case uses this structure:

```json
{
  "case_id": "QA-001",
  "question": "A document-grounded question",
  "document_ids": ["authorized MongoDB document IDs"],
  "expected_answerable": true,
  "expected_source_documents": ["manually verified document IDs"],
  "actual_answerable": true,
  "actual_source_documents": ["document IDs returned by the API"],
  "claim_support": [true, true],
  "notes": "Reviewer notes"
}
```

From `backend/`, calculate metrics from completed labels with:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_answers.py ..\data\evaluation\answer_verification_cases.json
```

The utility reports answerability accuracy, abstention success, citation-document
accuracy, and unsupported-claim rate. It does not call Gemini or process CUAD.
