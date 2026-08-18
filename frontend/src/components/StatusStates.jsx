export function LoadingState() {
  return (
    <div className="skeleton-grid" role="status" aria-label="Loading job listings">
      {Array.from({ length: 6 }).map((_, i) => (
        <div className="skeleton-card" key={i} />
      ))}
    </div>
  );
}

export function EmptyState({ hasFilters, onClear }) {
  return (
    <div className="status-panel">
      <p className="status-panel__code">board · no departures</p>
      <h2 className="status-panel__title">No listings match this search</h2>
      <p className="status-panel__body">
        {hasFilters
          ? "Try widening your search — clear a filter or use a broader keyword."
          : "The board is empty. Run an ingestion to pull the latest listings from Remotive."}
      </p>
      {hasFilters && (
        <button
          onClick={onClear}
          style={{
            marginTop: 14,
            fontFamily: "var(--font-mono)",
            fontSize: 12.5,
            padding: "8px 14px",
            border: "1px solid var(--line)",
            borderRadius: 6,
            background: "#fff",
            cursor: "pointer",
          }}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="status-panel status-panel--error">
      <p className="status-panel__code">board · signal lost</p>
      <h2 className="status-panel__title">Couldn't reach the job board API</h2>
      <p className="status-panel__body">{message}</p>
      <button
        onClick={onRetry}
        style={{
          marginTop: 14,
          fontFamily: "var(--font-mono)",
          fontSize: 12.5,
          padding: "8px 14px",
          border: "1px solid var(--brick)",
          color: "var(--brick)",
          borderRadius: 6,
          background: "#fff",
          cursor: "pointer",
        }}
      >
        Retry
      </button>
    </div>
  );
}
