export default function Controls({ filters, onChange, resultCount, total }) {
  const update = (key) => (e) => onChange({ ...filters, [key]: e.target.value });

  return (
    <div className="controls">
      <div className="controls__row">
        <label style={{ flex: "1 1 220px" }}>
          <span className="controls__search-label">Search</span>
          <input
            type="text"
            placeholder="Title, company, or keyword..."
            value={filters.search}
            onChange={update("search")}
          />
        </label>

        <label>
          <span className="controls__search-label">Job type</span>
          <select value={filters.jobType} onChange={update("jobType")}>
            <option value="">Any</option>
            <option value="full_time">Full-time</option>
            <option value="part_time">Part-time</option>
            <option value="contract">Contract</option>
            <option value="freelance">Freelance</option>
            <option value="internship">Internship</option>
          </select>
        </label>

        <label>
          <span className="controls__search-label">Location</span>
          <input
            type="text"
            placeholder="e.g. USA, Worldwide"
            value={filters.location}
            onChange={update("location")}
          />
        </label>

        <label>
          <span className="controls__search-label">Category</span>
          <input
            type="text"
            placeholder="e.g. Design"
            value={filters.category}
            onChange={update("category")}
          />
        </label>
      </div>
      <p className="controls__meta">
        showing {resultCount} of {total} listing{total === 1 ? "" : "s"}
      </p>
    </div>
  );
}
