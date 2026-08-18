export default function Header({ totalJobs, health }) {
  const statusDot = health === "ok" ? "dot--ok" : health === "error" ? "dot--err" : "dot--warn";
  const statusLabel = health === "ok" ? "connected" : health === "error" ? "unreachable" : "checking...";

  return (
    <header className="masthead">
      <div className="masthead__inner">
        <p className="masthead__eyebrow">Remote job board · live feed</p>
        <h1 className="masthead__title">Remote Departures</h1>
        <p className="masthead__subtitle">
          Real listings pulled directly from the public Remotive API — no scraped
          accounts, no fabricated data.
        </p>
        <div className="board-status">
          <span>
            <span className={`dot ${statusDot}`} />
            api: <strong>{statusLabel}</strong>
          </span>
          <span>
            listings on board: <strong>{totalJobs}</strong>
          </span>
          <span>source: <strong>Remotive</strong></span>
        </div>
      </div>
    </header>
  );
}
