/**
 * UploadPanel — PDF file upload with loading, success, and error states.
 *
 * Rules:
 * - PDF-only file input.
 * - Does NOT set Content-Type manually for FormData (browser handles boundary).
 * - Clears file input and shows success message on successful upload.
 * - Disables button while uploading to prevent duplicate submissions.
 * - Notifies parent to refresh document list via onUploaded callback.
 */

import { FormEvent, useRef, useState } from "react";
import { api } from "../services/api";

interface UploadPanelProps {
  onUploaded: () => void;
}

export function UploadPanel({ onUploaded }: UploadPanelProps) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; kind: "success" | "error" } | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string>("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = () => {
    const file = inputRef.current?.files?.[0];
    setSelectedFileName(file ? file.name : "");
    setMessage(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    setBusy(true);
    setMessage(null);
    try {
      await api.uploadDocument(file);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
      setSelectedFileName("");
      setMessage({ text: "PDF uploaded successfully.", kind: "success" });
      onUploaded();
    } catch (err) {
      setMessage({
        text: err instanceof Error ? err.message : "Upload failed. Please try again.",
        kind: "error",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel" aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload a PDF</h2>

      <form onSubmit={handleSubmit} className="upload-form">
        <label htmlFor="pdf-file-input" className="upload-file-label">
          <span className="upload-file-label__text">
            {selectedFileName ? selectedFileName : "Choose a PDF file…"}
          </span>
          <input
            id="pdf-file-input"
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            required
            onChange={handleFileChange}
            aria-describedby={message ? "upload-message" : undefined}
          />
        </label>
        <button type="submit" disabled={busy || !selectedFileName}>
          {busy ? "Uploading…" : "Upload PDF"}
        </button>
      </form>

      {message && (
        <p
          id="upload-message"
          className={message.kind === "success" ? "notice notice--success" : "notice notice--error"}
          role={message.kind === "error" ? "alert" : "status"}
        >
          {message.text}
        </p>
      )}
    </section>
  );
}
