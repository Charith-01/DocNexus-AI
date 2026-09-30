/**
 * DocNexus AI — Frontend API service layer.
 *
 * Single source of truth for all HTTP communication with the FastAPI backend.
 * All methods are derived from actual backend route implementations.
 *
 * Authentication:  sessionStorage via the `session` helper.
 * Token transport: Authorization: Bearer <token> on every authenticated call.
 * Error handling:  ApiError is thrown for all non-2xx responses and network
 *                  failures.  The caller receives a typed error with a clean
 *                  message and the HTTP status code where available.
 */

import type {
  AnswerQueryRequest,
  AnswerResponse,
  DocumentIntelligenceResult,
  DocumentListResponse,
  DocumentResponse,
  IndexDocumentResponse,
  IndexStatusResponse,
  OrchestratorRouteResponse,
  RetrievalSearchRequest,
  RetrievalSearchResponse,
  TokenResponse,
  UploadResponse,
  User,
} from "../types/api";

// ─── Base URL ────────────────────────────────────────────────────────────────

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

// ─── Session (token storage) ─────────────────────────────────────────────────

const TOKEN_KEY = "docnexus_access_token";

/**
 * Thin wrapper around sessionStorage for the JWT access token.
 * We use sessionStorage (not localStorage) because the existing project
 * already established this pattern; do not change storage without reason.
 */
export const session = {
  getToken: (): string | null => sessionStorage.getItem(TOKEN_KEY),
  setToken: (token: string): void => sessionStorage.setItem(TOKEN_KEY, token),
  clear: (): void => sessionStorage.removeItem(TOKEN_KEY),
};

// ─── Normalized API Error ─────────────────────────────────────────────────────

export class ApiRequestError extends Error {
  /** HTTP status code (undefined for network failures). */
  readonly status: number | undefined;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

// ─── Shared HTTP helper ───────────────────────────────────────────────────────

/**
 * Core fetch wrapper used by all API methods.
 *
 * Responsibilities:
 * - Automatically sets Content-Type: application/json for JSON bodies.
 * - Does NOT set Content-Type for FormData (browser generates the boundary).
 * - Injects Authorization: Bearer <token> when `authenticated` is true.
 * - On HTTP 401 with an authenticated request: clears the session and
 *   dispatches `docnexus:auth-expired` so the app can redirect to login.
 * - On any non-2xx response: parses backend { detail: string } and throws
 *   ApiRequestError with the backend message and HTTP status.
 * - On HTTP 204 No Content: returns undefined cast as T.
 * - On network failure: throws ApiRequestError with a user-friendly message.
 */
async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const headers = new Headers(options.headers);

  // Set Content-Type for JSON bodies only; skip for FormData.
  if (!(options.body instanceof FormData) && options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  // Inject Bearer token for authenticated endpoints.
  if (authenticated) {
    const token = session.getToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    // Network failure (no HTTP status available).
    throw new ApiRequestError(
      "Network error — could not reach the server. Check your connection.",
    );
  }

  // Handle session expiry: clear state and notify the app.
  if (response.status === 401 && authenticated) {
    session.clear();
    window.dispatchEvent(new Event("docnexus:auth-expired"));
    throw new ApiRequestError("Session expired. Please log in again.", 401);
  }

  // Successful empty response (e.g. DELETE returning 204).
  if (response.status === 204) {
    return undefined as T;
  }

  // Parse error body for every non-2xx response.
  if (!response.ok) {
    let message = "Request failed";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body?.detail === "string" && body.detail.trim()) {
        message = body.detail.trim();
      }
    } catch {
      // Body is not valid JSON — fall back to generic message.
    }
    throw new ApiRequestError(message, response.status);
  }

  return response.json() as Promise<T>;
}

// ─── API Methods ──────────────────────────────────────────────────────────────

export const api = {
  // ── AUTH ──────────────────────────────────────────────────────────────────

  /**
   * POST /auth/register
   * Creates a new user account.  Returns the created UserResponse.
   */
  register: (email: string, password: string): Promise<User> =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  /**
   * POST /auth/login
   * Authenticates and returns a JWT access token.
   */
  login: (email: string, password: string): Promise<TokenResponse> =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  /**
   * GET /auth/me
   * Returns the authenticated user's profile.
   */
  me: (): Promise<User> => request<User>("/auth/me", {}, true),

  // ── DOCUMENTS ─────────────────────────────────────────────────────────────

  /**
   * GET /documents
   * Lists all documents owned by or shared with the current user.
   */
  listDocuments: (): Promise<DocumentListResponse> =>
    request<DocumentListResponse>("/documents", {}, true),

  /**
   * GET /documents/{document_id}
   * Returns metadata for a single accessible document.
   */
  getDocument: (documentId: string): Promise<DocumentResponse> =>
    request<DocumentResponse>(`/documents/${documentId}`, {}, true),

  /**
   * POST /documents/upload
   * Uploads a PDF file.  Uses multipart/form-data — Content-Type header is
   * intentionally omitted so the browser generates the multipart boundary.
   */
  uploadDocument: (file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>(
      "/documents/upload",
      { method: "POST", body: form },
      true,
    );
  },

  /**
   * DELETE /documents/{document_id}
   * Deletes the document record, its stored PDF file, and all index data.
   * Returns 204 No Content on success.
   */
  deleteDocument: (documentId: string): Promise<void> =>
    request<void>(`/documents/${documentId}`, { method: "DELETE" }, true),

  // ── DOCUMENT INTELLIGENCE ─────────────────────────────────────────────────

  /**
   * POST /documents/{document_id}/process
   * Triggers synchronous PDF processing + NLP analysis for the document.
   * Returns the full DocumentIntelligenceResult on success.
   *
   * HTTP error semantics:
   *   404 — document not found or no access
   *   403 — access denied
   *   409 — already processing, or intelligence not available
   *   422 — text not extractable / source unavailable
   *   503 — spaCy model unavailable
   *   500 — processing failed
   */
  processDocument: (documentId: string): Promise<DocumentIntelligenceResult> =>
    request<DocumentIntelligenceResult>(
      `/documents/${documentId}/process`,
      { method: "POST" },
      true,
    ),

  /**
   * GET /documents/{document_id}/intelligence
   * Returns previously stored intelligence results without re-processing.
   *
   * HTTP error semantics: same as processDocument.
   */
  getDocumentIntelligence: (
    documentId: string,
  ): Promise<DocumentIntelligenceResult> =>
    request<DocumentIntelligenceResult>(
      `/documents/${documentId}/intelligence`,
      {},
      true,
    ),

  // ── RETRIEVAL / INDEXING ──────────────────────────────────────────────────

  /**
   * POST /documents/{document_id}/index
   * Chunks, embeds, and indexes the document for retrieval.
   * The document must have been successfully processed first.
   *
   * HTTP error semantics:
   *   404 — document not found
   *   403 — access denied
   *   409 — not yet processed, or already indexing
   *   500 — indexing failed
   */
  indexDocument: (documentId: string): Promise<IndexDocumentResponse> =>
    request<IndexDocumentResponse>(
      `/documents/${documentId}/index`,
      { method: "POST" },
      true,
    ),

  /**
   * GET /documents/{document_id}/index-status
   * Returns the current indexing status for the document.
   */
  getIndexStatus: (documentId: string): Promise<IndexStatusResponse> =>
    request<IndexStatusResponse>(
      `/documents/${documentId}/index-status`,
      {},
      true,
    ),

  /**
   * DELETE /documents/{document_id}/index
   * Removes the document's index data from ChromaDB and BM25.
   * Returns 204 No Content on success.
   */
  deleteDocumentIndex: (documentId: string): Promise<void> =>
    request<void>(
      `/documents/${documentId}/index`,
      { method: "DELETE" },
      true,
    ),

  // ── RETRIEVAL SEARCH ──────────────────────────────────────────────────────

  /**
   * POST /retrieval/search
   * Performs ranked retrieval across the current user's indexed documents.
   *
   * The backend enforces ownership; do not send owner_id from the frontend.
   *
   * HTTP error semantics:
   *   500 — retrieval operation failed
   */
  searchDocuments: (
    payload: RetrievalSearchRequest,
  ): Promise<RetrievalSearchResponse> =>
    request<RetrievalSearchResponse>(
      "/retrieval/search",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  // ── ANSWER & VERIFICATION ─────────────────────────────────────────────────

  /**
   * POST /answers/query
   * Performs grounded RAG answer generation with Gemini + claim verification.
   *
   * HTTP error semantics:
   *   404 — document not found
   *   403 — document access denied
   *   500 — retrieval operation failed
   *   503 — LLM provider temporarily unavailable
   *   502 — LLM returned an invalid response
   */
  answerQuery: (payload: AnswerQueryRequest): Promise<AnswerResponse> =>
    request<AnswerResponse>(
      "/answers/query",
      { method: "POST", body: JSON.stringify(payload) },
      true,
    ),

  // ── ORCHESTRATOR ──────────────────────────────────────────────────────────

  /**
   * POST /orchestrator/route
   * Routes the query to the appropriate agent and returns the intent +
   * next workflow steps.  Does NOT execute the agent.
   *
   * HTTP error semantics:
   *   403 — one or more document_ids are inaccessible
   */
  routeQuery: (
    query: string,
    documentIds: string[],
  ): Promise<OrchestratorRouteResponse> =>
    request<OrchestratorRouteResponse>(
      "/orchestrator/route",
      {
        method: "POST",
        body: JSON.stringify({ query, document_ids: documentIds }),
      },
      true,
    ),
};
