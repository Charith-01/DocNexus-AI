/**
 * DocNexus AI — Frontend TypeScript contracts.
 *
 * Every interface in this file is derived directly from the corresponding
 * backend Pydantic schema.  Field names, optionality, and literal unions
 * must stay in sync with the backend.  Do not invent fields here.
 *
 * Sections:
 *   AUTH
 *   DOCUMENTS
 *   DOCUMENT INTELLIGENCE
 *   RETRIEVAL / INDEXING
 *   ANSWER & VERIFICATION
 *   ORCHESTRATOR
 *   ERRORS
 */

// ─── AUTH ────────────────────────────────────────────────────────────────────

/** POST /auth/register  — request body (UserRegistration) */
export interface RegisterRequest {
  email: string;
  password: string;
}

/** POST /auth/login  — request body (UserLogin) */
export interface LoginRequest {
  email: string;
  password: string;
}

/** GET /auth/me  — response body (UserResponse) */
export interface User {
  id: string;
  email: string;
  created_at: string; // ISO-8601 datetime string from the backend
}

/** POST /auth/login  — response body (TokenResponse) */
export interface TokenResponse {
  access_token: string;
  token_type: string; // always "bearer"
}

/** @deprecated Use TokenResponse instead. */
export type AuthToken = TokenResponse;

// ─── DOCUMENTS ───────────────────────────────────────────────────────────────

/**
 * Document processing status values that may appear in DocumentResponse.status.
 * The backend stores these as plain strings; this union makes them explicit.
 */
export type ProcessingStatus =
  | "uploaded"
  | "processing"
  | "processed"
  | "processing_failed";

/**
 * Document retrieval / indexing status values.
 * Mirrors backend IndexStatusResponse.retrieval_status literal.
 */
export type RetrievalStatus =
  | "not_indexed"
  | "indexing"
  | "indexed"
  | "index_failed";

/** Single document record (DocumentResponse) */
export interface DocumentResponse {
  id: string;
  owner_id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  sha256: string;
  status: string; // ProcessingStatus; kept as string to tolerate future values
  created_at: string; // ISO-8601
  updated_at: string; // ISO-8601
}

/** GET /documents  — response body (DocumentListResponse) */
export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

/** POST /documents/upload  — response body (UploadResponse) */
export interface UploadResponse {
  message: string;
  document: DocumentResponse;
}

// Aliases kept so existing UI code that imports these names continues to compile.
/** @deprecated Use DocumentResponse instead. */
export type DocumentRecord = DocumentResponse;
/** @deprecated Use DocumentListResponse instead. */
export type DocumentList = DocumentListResponse;
/** @deprecated Use UploadResponse instead. */
export type UploadResult = UploadResponse;

// ─── DOCUMENT INTELLIGENCE ───────────────────────────────────────────────────

/** Single named entity extracted by spaCy (IntelligenceEntity) */
export interface IntelligenceEntity {
  text: string;
  label: string;
  page: number; // 1-indexed
}

/** Named-entity groups returned by the intelligence agent (EntityGroups) */
export interface EntityGroups {
  people: IntelligenceEntity[];
  organizations: IntelligenceEntity[];
  locations: IntelligenceEntity[];
  dates: IntelligenceEntity[];
  money: IntelligenceEntity[];
  other: IntelligenceEntity[];
}

/** PDF embedded metadata extracted by PyMuPDF (PDFMetadata) */
export interface PDFMetadata {
  title: string | null;
  author: string | null;
  subject: string | null;
  keywords: string | null;
  creator: string | null;
  producer: string | null;
  creation_date: string | null;
  modification_date: string | null;
}

/**
 * Full intelligence result returned by:
 *   POST /documents/{document_id}/process
 *   GET  /documents/{document_id}/intelligence
 * (DocumentIntelligenceResult)
 */
export interface DocumentIntelligenceResult {
  document_id: string;
  status: "processed";
  document_type: string;
  classification_confidence: number; // [0, 1]
  summary: string;
  keywords: string[];
  entities: EntityGroups;
  pdf_metadata: PDFMetadata;
  page_count: number;
  word_count: number;
  character_count: number;
  is_text_extractable: boolean;
  requires_ocr: boolean;
  processed_at: string; // ISO-8601
}

// ─── RETRIEVAL / INDEXING ─────────────────────────────────────────────────────

/** Retrieval mode values (RetrievalMode StrEnum) */
export type RetrievalMode = "semantic" | "bm25" | "hybrid";

/**
 * POST /documents/{document_id}/index  — response body (IndexResponse)
 * Note: the backend field is retrieval_status (not status).
 */
export interface IndexDocumentResponse {
  document_id: string;
  retrieval_status: "indexed";
  indexed_chunk_count: number;
  embedding_model: string;
  indexed_at: string; // ISO-8601
}

/**
 * GET /documents/{document_id}/index-status  — response body (IndexStatusResponse)
 */
export interface IndexStatusResponse {
  document_id: string;
  retrieval_status: RetrievalStatus;
  indexed_chunk_count: number;
  embedding_model: string | null;
  indexed_at: string | null; // ISO-8601 or null
}

/** Single ranked retrieval result (RetrievalResult) */
export interface RetrievalResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  chunk_index: number;
  text: string;
  semantic_score: number | null;
  bm25_score: number | null;
  hybrid_score: number | null;
}

/**
 * POST /retrieval/search  — request body (RetrievalSearchRequest)
 * The owner_id is resolved server-side; do not send it from the frontend.
 */
export interface RetrievalSearchRequest {
  query: string; // 1-2000 characters, must not be blank
  document_ids?: string[]; // optional filter; max 100 items
  mode?: RetrievalMode; // default "hybrid"
  top_k?: number; // default 5, range 1-20
}

/** POST /retrieval/search  — response body (RetrievalSearchResponse) */
export interface RetrievalSearchResponse {
  query: string;
  mode: RetrievalMode;
  result_count: number;
  results: RetrievalResult[];
}

// ─── ANSWER & VERIFICATION ───────────────────────────────────────────────────

/** Verification status values (VerificationStatus StrEnum) */
export type VerificationStatus =
  | "verified"
  | "partially_supported"
  | "insufficient_evidence"
  | "unverified";

/**
 * POST /answers/query  — request body (AnswerRequest)
 * The backend uses extra="forbid", so only these fields are allowed.
 */
export interface AnswerQueryRequest {
  query: string; // 1-ANSWER_MAX_QUERY_LENGTH chars, must not be blank
  document_ids?: string[]; // optional filter; max 100 items
  retrieval_mode?: RetrievalMode; // default "hybrid"
  top_k?: number; // default ANSWER_DEFAULT_TOP_K, range 1-ANSWER_MAX_TOP_K
}

/**
 * A single citation linking answer text to a source document chunk (Citation).
 * Does not expose the raw chunk text - that is in EvidenceSource (server-only).
 */
export interface AnswerCitation {
  source_id: string; // e.g. "S1", "S2"
  document_id: string;
  filename: string;
  page_number: number;
  chunk_id: string;
}

/** POST /answers/query  — response body (AnswerResponse) */
export interface AnswerResponse {
  query: string;
  answer: string;
  answerable: boolean;
  verification_status: VerificationStatus;
  citations: AnswerCitation[];
  warnings: string[];
  supported_claim_count: number;
  unsupported_claim_count: number;
}

// ─── ORCHESTRATOR ─────────────────────────────────────────────────────────────

/** Intent values (Intent StrEnum) */
export type OrchestratorIntent =
  | "summarize_document"
  | "analyze_document"
  | "search_documents"
  | "ask_question"
  | "compare_documents"
  | "unknown";

/** Agent name values (AgentName StrEnum) */
export type AgentName =
  | "document_intelligence"
  | "retrieval"
  | "answer_verification"
  | "none";

/** POST /orchestrator/route  — request body (QueryRouteRequest) */
export interface OrchestratorRouteRequest {
  query: string; // 1-4000 characters, must not be blank
  document_ids?: string[]; // optional; max 100 items
}

/** POST /orchestrator/route  — response body (QueryRouteResponse) */
export interface OrchestratorRouteResponse {
  request_id: string;
  intent: OrchestratorIntent;
  target_agent: AgentName;
  next_steps: AgentName[];
}

/** @deprecated Use OrchestratorRouteResponse instead. */
export type RouteResult = OrchestratorRouteResponse;

// ─── ERRORS ───────────────────────────────────────────────────────────────────

/**
 * Normalized API error exposed to UI components.
 * Constructed by the api service from backend { detail: string } or
 * from network failures.
 */
export interface ApiError {
  /** Human-readable message suitable for display. */
  message: string;
  /** HTTP status code if available, undefined for network failures. */
  status?: number;
}
