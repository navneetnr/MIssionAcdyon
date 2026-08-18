import { useEffect, useState, useCallback } from "react";
import Header from "./components/Header.jsx";
import Controls from "./components/Controls.jsx";
import JobCard from "./components/JobCard.jsx";
import { LoadingState, EmptyState, ErrorState } from "./components/StatusStates.jsx";
import { fetchJobs, fetchHealth } from "./api.js";

const PAGE_SIZE = 12;

const EMPTY_FILTERS = { search: "", jobType: "", location: "", category: "" };

export default function App() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("loading"); // loading | ready | empty | error
  const [errorMessage, setErrorMessage] = useState("");
  const [health, setHealth] = useState("checking");

  const loadJobs = useCallback((activeFilters) => {
    setStatus("loading");
    fetchJobs({
      search: activeFilters.search || undefined,
      jobType: activeFilters.jobType || undefined,
      location: activeFilters.location || undefined,
      category: activeFilters.category || undefined,
      limit: PAGE_SIZE,
      offset: 0,
    })
      .then((data) => {
        setJobs(data.jobs);
        setTotal(data.total);
        setStatus(data.jobs.length === 0 ? "empty" : "ready");
      })
      .catch((err) => {
        setErrorMessage(err.message || "Unknown error");
        setStatus("error");
      });
  }, []);

  // debounce filter changes so we don't fire a request per keystroke
  useEffect(() => {
    const id = setTimeout(() => loadJobs(filters), 300);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, loadJobs]);

  useEffect(() => {
    fetchHealth()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("error"));
  }, []);

  const hasActiveFilters = Object.values(filters).some((v) => v);

  return (
    <>
      <Header totalJobs={total} health={health} />
      <Controls
        filters={filters}
        onChange={setFilters}
        resultCount={jobs.length}
        total={total}
      />

      {status === "loading" && <LoadingState />}

      {status === "error" && (
        <ErrorState message={errorMessage} onRetry={() => loadJobs(filters)} />
      )}

      {status === "empty" && (
        <EmptyState hasFilters={hasActiveFilters} onClear={() => setFilters(EMPTY_FILTERS)} />
      )}

      {status === "ready" && (
        <div className="job-grid">
          {jobs.map((job) => (
            <JobCard key={`${job.source}-${job.external_id}`} job={job} />
          ))}
        </div>
      )}

      <footer className="site-footer">
        data via the public Remotive API · original listings linked, not reproduced
      </footer>
    </>
  );
}
