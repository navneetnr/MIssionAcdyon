function formatDate(iso) {
  if (!iso) return "date n/a";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatJobType(jobType) {
  if (!jobType) return null;
  return jobType.replace(/_/g, " ");
}

export default function JobCard({ job }) {
  return (
    <article className="job-card">
      <div className="job-card__main">
        <h2 className="job-card__title">{job.title}</h2>
        <p className="job-card__company">{job.company}</p>

        <div className="job-card__meta-row">
          {job.location && <span>📍 {job.location}</span>}
          {job.job_type && <span>🕒 {formatJobType(job.job_type)}</span>}
          {job.salary && <span>💰 {job.salary}</span>}
        </div>

        {job.description && (
          <p className="job-card__description">
            {job.description.replace(/<[^>]+>/g, "").slice(0, 180)}
          </p>
        )}

        {job.tags && job.tags.length > 0 && (
          <div className="job-card__tags">
            {job.tags.slice(0, 4).map((tag) => (
              <span key={tag} className="job-card__tag">
                {tag}
              </span>
            ))}
          </div>
        )}

        <a
          className="job-card__link"
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          View original listing →
        </a>
      </div>

      <div className="job-card__stub" aria-hidden="false">
        <span className="job-card__source">{job.source}</span>
        <span className="job-card__stub-code">{formatDate(job.posted_date)}</span>
      </div>
    </article>
  );
}
