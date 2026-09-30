/**
 * DocumentStatusBadge — reusable status pill for processing and retrieval
 * statuses. Uses readable text + colour coding. No colour-only meaning.
 */

interface ProcessingBadgeProps {
  status: string;
}

/** Maps backend status strings to display label + CSS modifier class. */
function processingConfig(status: string): { label: string; mod: string } {
  switch (status) {
    case "uploaded":
      return { label: "Uploaded", mod: "neutral" };
    case "processing":
      return { label: "Processing…", mod: "progress" };
    case "processed":
      return { label: "Processed", mod: "success" };
    case "processing_failed":
      return { label: "Processing Failed", mod: "error" };
    default:
      return { label: status, mod: "neutral" };
  }
}

function retrievalConfig(status: string): { label: string; mod: string } {
  switch (status) {
    case "not_indexed":
      return { label: "Not Indexed", mod: "neutral" };
    case "indexing":
      return { label: "Indexing…", mod: "progress" };
    case "indexed":
      return { label: "Indexed", mod: "success" };
    case "index_failed":
      return { label: "Index Failed", mod: "error" };
    default:
      return { label: status, mod: "neutral" };
  }
}

export function ProcessingStatusBadge({ status }: ProcessingBadgeProps) {
  const { label, mod } = processingConfig(status);
  return (
    <span className={`status-badge status-badge--${mod}`} aria-label={`Processing status: ${label}`}>
      {label}
    </span>
  );
}

interface RetrievalBadgeProps {
  status: string;
}

export function RetrievalStatusBadge({ status }: RetrievalBadgeProps) {
  const { label, mod } = retrievalConfig(status);
  return (
    <span className={`status-badge status-badge--${mod} status-badge--sm`} aria-label={`Retrieval status: ${label}`}>
      {label}
    </span>
  );
}
