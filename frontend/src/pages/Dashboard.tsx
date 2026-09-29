import { FormEvent, useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type { DocumentRecord, RouteResult, User } from "../types/api";

interface DashboardProps {
  user: User;
  onLogout: () => void;
}

export function Dashboard({ user, onLogout }: DashboardProps) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      const result = await api.listDocuments();
      setDocuments(result.documents);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load documents");
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("pdf") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      await api.uploadDocument(file);
      input.value = "";
      setMessage("PDF uploaded successfully.");
      await loadDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (documentId: string) => {
    setMessage("");
    try {
      await api.deleteDocument(documentId);
      setSelectedIds((ids) => ids.filter((id) => id !== documentId));
      await loadDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Delete failed");
    }
  };

  const submitQuery = async (event: FormEvent) => {
    event.preventDefault();
    setMessage("");
    try {
      setRoute(await api.routeQuery(query, selectedIds));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Routing failed");
    }
  };

  const toggleDocument = (id: string) => {
    setSelectedIds((ids) =>
      ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id],
    );
  };

  return (
    <main className="dashboard">
      <header>
        <div>
          <p className="eyebrow">DocNexus AI</p>
          <h1>Document workspace</h1>
          <p className="muted">Signed in as {user.email}</p>
        </div>
        <button className="secondary" onClick={onLogout}>Logout</button>
      </header>

      {message && <p className="notice">{message}</p>}

      <section className="panel">
        <h2>Upload a PDF</h2>
        <form className="upload-row" onSubmit={upload}>
          <input name="pdf" type="file" accept="application/pdf,.pdf" required />
          <button disabled={busy}>{busy ? "Uploading…" : "Upload"}</button>
        </form>
      </section>

      <section className="panel">
        <h2>Your documents</h2>
        {documents.length === 0 ? (
          <p className="muted">No documents uploaded yet.</p>
        ) : (
          <ul className="document-list">
            {documents.map((document) => (
              <li key={document.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(document.id)}
                    onChange={() => toggleDocument(document.id)}
                  />
                  <span>
                    <strong>{document.original_filename}</strong>
                    <small>{Math.ceil(document.file_size / 1024)} KB · {document.status}</small>
                  </span>
                </label>
                <button className="danger" onClick={() => void remove(document.id)}>Delete</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h2>AI query router</h2>
        <p className="muted">Select relevant documents above, then preview which agent will handle your request.</p>
        <form onSubmit={submitQuery}>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What does this agreement say about termination?"
            required
          />
          <button>Route query</button>
        </form>
        {route && (
          <div className="route-result">
            <strong>Intent:</strong> {route.intent}<br />
            <strong>Target:</strong> {route.target_agent}<br />
            <strong>Next steps:</strong> {route.next_steps.join(" → ") || "None"}
          </div>
        )}
      </section>
    </main>
  );
}
