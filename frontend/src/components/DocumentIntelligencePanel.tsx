/**
 * DocumentIntelligencePanel — modal drawer showing the full intelligence result.
 *
 * Displays:
 * - Document type + classification confidence
 * - Extractive Summary (labelled correctly — NOT "AI-generated")
 * - Keywords as chips
 * - Statistics (page count, word count, character count)
 * - PDF metadata (only non-null fields shown)
 * - OCR / text extractability notice
 * - Named entity groups (people, organizations, locations, dates, money, other)
 * - Processing timestamp
 *
 * Closes on Escape or backdrop click for accessible keyboard behavior.
 */

import { useEffect } from "react";
import type { DocumentIntelligenceResult, IntelligenceEntity } from "../types/api";

interface DocumentIntelligencePanelProps {
  result: DocumentIntelligenceResult;
  filename: string;
  onClose: () => void;
}

interface EntityGroupProps {
  title: string;
  entities: IntelligenceEntity[];
}

function EntityGroup({ title, entities }: EntityGroupProps) {
  if (entities.length === 0) return null;
  return (
    <div className="intel-entity-group">
      <h4 className="intel-entity-group__title">{title}</h4>
      <ul className="intel-entity-list">
        {entities.map((entity, idx) => (
          <li key={idx} className="intel-entity-item">
            <span className="intel-entity-item__text">{entity.text}</span>
            <span className="intel-entity-item__meta">
              <span className="intel-entity-item__label">{entity.label}</span>
              <span className="intel-entity-item__page">p.{entity.page}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DocumentIntelligencePanel({
  result,
  filename,
  onClose,
}: DocumentIntelligencePanelProps) {
  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Prevent body scroll while modal open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  const { entities, pdf_metadata } = result;

  // Check whether any entity group has content
  const hasEntities =
    entities.people.length > 0 ||
    entities.organizations.length > 0 ||
    entities.locations.length > 0 ||
    entities.dates.length > 0 ||
    entities.money.length > 0 ||
    entities.other.length > 0;

  // Only show metadata fields that are non-null and non-empty
  const metaFields: { label: string; value: string | null }[] = [
    { label: "Title", value: pdf_metadata.title },
    { label: "Author", value: pdf_metadata.author },
    { label: "Subject", value: pdf_metadata.subject },
    { label: "Creator", value: pdf_metadata.creator },
    { label: "Producer", value: pdf_metadata.producer },
    { label: "Keywords", value: pdf_metadata.keywords },
    { label: "Created", value: pdf_metadata.creation_date },
    { label: "Modified", value: pdf_metadata.modification_date },
  ].filter((f) => f.value && f.value.trim());

  const processedAt = new Date(result.processed_at).toLocaleString();
  const confidencePct = Math.round(result.classification_confidence * 100);

  return (
    <>
      {/* Backdrop */}
      <div
        className="intel-backdrop"
        onClick={onClose}
        role="presentation"
        aria-hidden="true"
      />

      {/* Panel drawer */}
      <div
        className="intel-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="intel-panel-title"
      >
        {/* Header */}
        <div className="intel-panel__header">
          <div>
            <p className="eyebrow">Document Intelligence</p>
            <h2 id="intel-panel-title" className="intel-panel__filename">
              {filename}
            </h2>
          </div>
          <button
            className="intel-close-btn"
            onClick={onClose}
            aria-label="Close document intelligence panel"
          >
            ✕
          </button>
        </div>

        {/* Scrollable body */}
        <div className="intel-panel__body">

          {/* Document type + confidence */}
          <section className="intel-section">
            <h3 className="intel-section__title">Classification</h3>
            <div className="intel-stats-row">
              <div className="intel-stat">
                <span className="intel-stat__label">Document Type</span>
                <span className="intel-stat__value intel-stat__value--prominent">{result.document_type}</span>
              </div>
              <div className="intel-stat">
                <span className="intel-stat__label">Confidence</span>
                <span className="intel-stat__value">{confidencePct}%</span>
              </div>
            </div>
          </section>

          {/* Text / OCR status */}
          {(!result.is_text_extractable || result.requires_ocr) && (
            <section className="intel-section">
              <div className="notice notice--warn" role="note">
                {result.requires_ocr && (
                  <p>
                    <strong>OCR Required:</strong> This PDF contains little or no
                    extractable text. OCR is not implemented in the current version.
                    Intelligence results may be limited.
                  </p>
                )}
                {!result.is_text_extractable && !result.requires_ocr && (
                  <p>
                    <strong>Text Not Extractable:</strong> Text could not be
                    extracted from this document.
                  </p>
                )}
              </div>
            </section>
          )}

          {/* Statistics */}
          <section className="intel-section">
            <h3 className="intel-section__title">Document Statistics</h3>
            <div className="intel-stats-row">
              <div className="intel-stat">
                <span className="intel-stat__label">Pages</span>
                <span className="intel-stat__value">{result.page_count}</span>
              </div>
              <div className="intel-stat">
                <span className="intel-stat__label">Words</span>
                <span className="intel-stat__value">{result.word_count.toLocaleString()}</span>
              </div>
              <div className="intel-stat">
                <span className="intel-stat__label">Characters</span>
                <span className="intel-stat__value">{result.character_count.toLocaleString()}</span>
              </div>
              <div className="intel-stat">
                <span className="intel-stat__label">Text Extractable</span>
                <span className="intel-stat__value">{result.is_text_extractable ? "Yes" : "No"}</span>
              </div>
              <div className="intel-stat">
                <span className="intel-stat__label">OCR Required</span>
                <span className="intel-stat__value">{result.requires_ocr ? "Yes" : "No"}</span>
              </div>
            </div>
          </section>

          {/* Extractive summary */}
          {result.summary && (
            <section className="intel-section">
              <h3 className="intel-section__title">Extractive Summary</h3>
              <p className="intel-summary">{result.summary}</p>
            </section>
          )}

          {/* Keywords */}
          <section className="intel-section">
            <h3 className="intel-section__title">Keywords</h3>
            {result.keywords.length > 0 ? (
              <div className="keyword-chips">
                {result.keywords.map((kw) => (
                  <span key={kw} className="keyword-chip">{kw}</span>
                ))}
              </div>
            ) : (
              <p className="muted">No keywords extracted.</p>
            )}
          </section>

          {/* Named Entities */}
          <section className="intel-section">
            <h3 className="intel-section__title">Named Entities</h3>
            {hasEntities ? (
              <div className="intel-entities">
                <EntityGroup title="People" entities={entities.people} />
                <EntityGroup title="Organizations" entities={entities.organizations} />
                <EntityGroup title="Locations" entities={entities.locations} />
                <EntityGroup title="Dates" entities={entities.dates} />
                <EntityGroup title="Money" entities={entities.money} />
                <EntityGroup title="Other" entities={entities.other} />
              </div>
            ) : (
              <p className="muted">No named entities extracted.</p>
            )}
          </section>

          {/* PDF Metadata */}
          {metaFields.length > 0 && (
            <section className="intel-section">
              <h3 className="intel-section__title">PDF Metadata</h3>
              <dl className="intel-meta-list">
                {metaFields.map((f) => (
                  <div key={f.label} className="intel-meta-row">
                    <dt className="intel-meta-row__label">{f.label}</dt>
                    <dd className="intel-meta-row__value">{f.value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          {/* Footer */}
          <p className="intel-processed-at muted">
            Processed at: {processedAt}
          </p>
        </div>
      </div>
    </>
  );
}
