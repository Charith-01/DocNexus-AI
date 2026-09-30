/**
 * Dashboard — primary workspace for authenticated users.
 *
 * Composes:
 *   - UploadPanel   (PDF upload with states)
 *   - DocumentList  (document cards + process/view/delete)
 *
 * The orchestrator query router section is preserved below the document list
 * for backward compatibility and will be expanded in later prompts.
 *
 * Do NOT add retrieval search, Q&A chat, or orchestrator execute here yet.
 */

import { FormEvent, useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type { DocumentResponse, OrchestratorRouteResponse, User } from "../types/api";
import { DocumentList } from "../components/DocumentList";
import { UploadPanel } from "../components/UploadPanel";

interface DashboardProps {
  user: User;
  onLogout: () => void;
}

export function Dashboard({ user, onLogout }: DashboardProps) {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [listError, setListError] = useState("");

  // Orchestrator preview state (existing feature — preserved)
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [route, setRoute] = useState<OrchestratorRouteResponse | null>(null);
  const [routeError, setRouteError] = useState("");

  // ── Load document list ─────────────────────────────────────────────────────
  const loadDocuments = useCallback(async () => {
    setListError("");
    setDocsLoading(true);
    try {
      const result = await api.listDocuments();
      setDocuments(result.documents);
    } catch (err) {
      setListError(
        err instanceof Error ? err.message : "Could not load documents.",
      );
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  // ── Refresh a single document record after processing ──────────────────────
  const handleDocumentUpdated = useCallback(async (documentId: string) => {
    try {
      const updated = await api.getDocument(documentId);
      setDocuments((prev) =>
        prev.map((d) => (d.id === documentId ? updated : d)),
      );
    } catch {
      // Silently fall back to a full list refresh if single fetch fails
      void loadDocuments();
    }
  }, [loadDocuments]);

  // ── Remove a document from state after delete ──────────────────────────────
  const handleDeleted = useCallback((documentId: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    setSelectedIds((prev) => prev.filter((id) => id !== documentId));
  }, []);

  // ── Orchestrator route preview ─────────────────────────────────────────────
  const submitQuery = async (event: FormEvent) => {
    event.preventDefault();
    setRouteError("");
    try {
      setRoute(await api.routeQuery(query, selectedIds));
    } catch (err) {
      setRouteError(
        err instanceof Error ? err.message : "Routing failed.",
      );
    }
  };

  const toggleDocument = (id: string) => {
    setSelectedIds((ids) =>
      ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id],
    );
  };

  return (
    <main className="dashboard">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="dashboard__header">
        <div>
          <p className="eyebrow">DocNexus AI</p>
          <h1>Document Workspace</h1>
          <p className="muted">Signed in as {user.email}</p>
        </div>
        <button className="secondary" onClick={onLogout}>
          Logout
        </button>
      </header>

      {/* ── Global list-level error ──────────────────────────────────────── */}
      {listError && (
        <p className="notice notice--error" role="alert">
          {listError}
        </p>
      )}

      {/* ── Upload ──────────────────────────────────────────────────────── */}
      <UploadPanel onUploaded={loadDocuments} />

      {/* ── Document list ────────────────────────────────────────────────── */}
      <DocumentList
        documents={documents}
        loading={docsLoading}
        onDeleted={handleDeleted}
        onDocumentUpdated={handleDocumentUpdated}
      />

      {/* ── Orchestrator query router preview (preserved) ────────────────── */}
      <section className="panel" aria-labelledby="router-heading">
        <h2 id="router-heading">AI Query Router</h2>
        <p className="muted">
          Select documents above, then preview which agent will handle your
          request. Full execution coming in a later update.
        </p>

        {/* Document selector for router */}
        {documents.length > 0 && (
          <div className="router-doc-selector">
            {documents.map((doc) => (
              <label key={doc.id} className="router-doc-label">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(doc.id)}
                  onChange={() => toggleDocument(doc.id)}
                />
                <span>{doc.original_filename}</span>
              </label>
            ))}
          </div>
        )}

        <form onSubmit={submitQuery} style={{ marginTop: "1rem" }}>
          <label htmlFor="router-query">Query</label>
          <textarea
            id="router-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What does this agreement say about termination?"
            required
          />
          <button type="submit">Route Query</button>
        </form>

        {routeError && (
          <p className="notice notice--error" role="alert">
            {routeError}
          </p>
        )}

        {route && (
          <div className="route-result">
            <strong>Intent:</strong> {route.intent}
            <br />
            <strong>Target Agent:</strong> {route.target_agent}
            <br />
            <strong>Next Steps:</strong>{" "}
            {route.next_steps.length > 0
              ? route.next_steps.join(" → ")
              : "None"}
          </div>
        )}
      </section>
    </main>
  );
}
