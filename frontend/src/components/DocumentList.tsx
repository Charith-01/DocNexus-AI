/**
 * DocumentList — displays the user's document cards with contextual actions.
 *
 * Each card shows:
 * - Filename, file size, upload date
 * - Processing status badge
 * - Process / View Intelligence / Delete actions
 *
 * Process button behaviour:
 * - "Process" when status is "uploaded" or "processing_failed" (retry)
 * - "Processing…" (disabled) when status is "processing"
 * - "View Intelligence" when status is "processed"
 *
 * Delete behaviour:
 * - Requires window.confirm() before deleting
 * - Removes document and closes any open intelligence panel for that doc
 * - Notifies parent via onDeleted callback
 */

import { useState } from "react";
import { api } from "../services/api";
import type { DocumentIntelligenceResult, DocumentResponse } from "../types/api";
import { DocumentIntelligencePanel } from "./DocumentIntelligencePanel";
import { ProcessingStatusBadge } from "./DocumentStatusBadge";

interface DocumentListProps {
  documents: DocumentResponse[];
  loading: boolean;
  onDeleted: (documentId: string) => void;
  onDocumentUpdated: (documentId: string) => void;
}

interface CardState {
  processingId: string | null; // which doc is currently being processed
  deletingId: string | null;   // which doc is currently being deleted
  errorMap: Record<string, string>; // per-document error messages
  intelligence: DocumentIntelligenceResult | null;
  intelligenceFilename: string;
  intelligenceLoading: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function DocumentList({
  documents,
  loading,
  onDeleted,
  onDocumentUpdated,
}: DocumentListProps) {
  const [state, setState] = useState<CardState>({
    processingId: null,
    deletingId: null,
    errorMap: {},
    intelligence: null,
    intelligenceFilename: "",
    intelligenceLoading: false,
  });

  const setDocError = (id: string, msg: string) =>
    setState((s) => ({ ...s, errorMap: { ...s.errorMap, [id]: msg } }));
  const clearDocError = (id: string) =>
    setState((s) => {
      const { [id]: _, ...rest } = s.errorMap;
      return { ...s, errorMap: rest };
    });

  // ── Process document ───────────────────────────────────────────────────────
  const handleProcess = async (doc: DocumentResponse) => {
    clearDocError(doc.id);
    setState((s) => ({ ...s, processingId: doc.id }));
    try {
      await api.processDocument(doc.id);
      onDocumentUpdated(doc.id); // tell parent to refresh this doc
    } catch (err) {
      setDocError(
        doc.id,
        err instanceof Error ? err.message : "Processing failed.",
      );
    } finally {
      setState((s) => ({ ...s, processingId: null }));
    }
  };

  // ── View intelligence ──────────────────────────────────────────────────────
  const handleViewIntelligence = async (doc: DocumentResponse) => {
    clearDocError(doc.id);
    setState((s) => ({
      ...s,
      intelligenceLoading: true,
      intelligenceFilename: doc.original_filename,
    }));
    try {
      const result = await api.getDocumentIntelligence(doc.id);
      setState((s) => ({
        ...s,
        intelligence: result,
        intelligenceLoading: false,
      }));
    } catch (err) {
      setState((s) => ({ ...s, intelligenceLoading: false }));
      setDocError(
        doc.id,
        err instanceof Error ? err.message : "Could not load intelligence results.",
      );
    }
  };

  // ── Delete document ────────────────────────────────────────────────────────
  const handleDelete = async (doc: DocumentResponse) => {
    if (
      !window.confirm(
        `Delete "${doc.original_filename}"?\n\nThis will permanently remove the file and all associated data.`,
      )
    ) {
      return;
    }
    clearDocError(doc.id);
    setState((s) => ({ ...s, deletingId: doc.id }));
    try {
      await api.deleteDocument(doc.id);
      // Close intelligence panel if it belongs to the deleted document
      setState((s) => ({
        ...s,
        deletingId: null,
        intelligence:
          s.intelligence?.document_id === doc.id ? null : s.intelligence,
      }));
      onDeleted(doc.id);
    } catch (err) {
      setDocError(
        doc.id,
        err instanceof Error ? err.message : "Delete failed.",
      );
      setState((s) => ({ ...s, deletingId: null }));
    }
  };

  const closeIntelligence = () =>
    setState((s) => ({ ...s, intelligence: null, intelligenceFilename: "" }));

  // ── Render ─────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <section className="panel" aria-label="Documents loading">
        <p className="muted" aria-live="polite">Loading documents…</p>
      </section>
    );
  }

  return (
    <>
      <section className="panel" aria-labelledby="doclist-heading">
        <h2 id="doclist-heading">Your Documents</h2>

        {documents.length === 0 ? (
          <p className="muted">No documents uploaded yet.</p>
        ) : (
          <ul className="doc-card-list" aria-label="Document list">
            {documents.map((doc) => {
              const isProcessing =
                state.processingId === doc.id || doc.status === "processing";
              const isDeleting = state.deletingId === doc.id;
              const isLoadingIntel =
                state.intelligenceLoading &&
                state.intelligenceFilename === doc.original_filename;
              const docError = state.errorMap[doc.id];

              return (
                <li key={doc.id} className="doc-card">
                  {/* ── Card header ─────────────────────────────────── */}
                  <div className="doc-card__header">
                    <div className="doc-card__info">
                      <strong className="doc-card__filename" title={doc.original_filename}>
                        {doc.original_filename}
                      </strong>
                      <span className="doc-card__meta">
                        {formatBytes(doc.file_size)}
                        {" · "}
                        {formatDate(doc.created_at)}
                      </span>
                    </div>
                    <ProcessingStatusBadge status={doc.status} />
                  </div>

                  {/* ── Per-doc error ────────────────────────────────── */}
                  {docError && (
                    <p className="doc-card__error" role="alert">
                      {docError}
                    </p>
                  )}

                  {/* ── Actions ─────────────────────────────────────── */}
                  <div className="doc-card__actions">
                    {/* Process / View Intelligence */}
                    {doc.status === "processed" ? (
                      <button
                        className="secondary"
                        onClick={() => void handleViewIntelligence(doc)}
                        disabled={isLoadingIntel}
                        aria-label={`View intelligence for ${doc.original_filename}`}
                      >
                        {isLoadingIntel ? "Loading…" : "View Intelligence"}
                      </button>
                    ) : doc.status === "processing" ? (
                      <button disabled aria-label="Document is currently processing">
                        Processing…
                      </button>
                    ) : (
                      /* uploaded or processing_failed — show Process (retry) */
                      <button
                        onClick={() => void handleProcess(doc)}
                        disabled={isProcessing}
                        aria-label={
                          doc.status === "processing_failed"
                            ? `Retry processing ${doc.original_filename}`
                            : `Process ${doc.original_filename}`
                        }
                      >
                        {isProcessing
                          ? "Processing…"
                          : doc.status === "processing_failed"
                          ? "Retry Processing"
                          : "Process Document"}
                      </button>
                    )}

                    {/* Delete */}
                    <button
                      className="danger"
                      onClick={() => void handleDelete(doc)}
                      disabled={isDeleting || isProcessing}
                      aria-label={`Delete ${doc.original_filename}`}
                    >
                      {isDeleting ? "Deleting…" : "Delete"}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* ── Intelligence panel (modal) ────────────────────────────────────── */}
      {state.intelligence && (
        <DocumentIntelligencePanel
          result={state.intelligence}
          filename={state.intelligenceFilename}
          onClose={closeIntelligence}
        />
      )}
    </>
  );
}
