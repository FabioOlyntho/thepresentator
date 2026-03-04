import { useState, useEffect, type CSSProperties } from 'react';
import { listJobs } from '../api';
import type { Job } from '../types';
import JobCard from '../components/JobCard';

export default function History() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [modeFilter, setModeFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const limit = 20;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listJobs({
      search: search || undefined,
      status: statusFilter || undefined,
      mode: modeFilter || undefined,
      limit,
      offset,
    })
      .then((res) => {
        if (!cancelled) {
          setJobs(res.jobs);
          setTotal(res.total);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [search, statusFilter, modeFilter, offset]);

  const hasMore = offset + limit < total;
  const hasPrev = offset > 0;

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>History</h1>

      {/* Filters */}
      <div style={styles.filters}>
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
          placeholder="Search by title..."
          style={styles.searchInput}
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
          style={styles.filterSelect}
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={modeFilter}
          onChange={(e) => { setModeFilter(e.target.value); setOffset(0); }}
          style={styles.filterSelect}
        >
          <option value="">All Modes</option>
          <option value="editable">Editable</option>
          <option value="ocr_editable">OCR + Editable</option>
          <option value="notebooklm">NotebookLM</option>
          <option value="full_slide">Full Slide</option>
          <option value="translate">Translate</option>
        </select>
        <div style={styles.count}>
          <span style={styles.countNum}>{total}</span> presentations
        </div>
      </div>

      {/* Job list */}
      {loading ? (
        <div style={styles.loading}>Loading...</div>
      ) : jobs.length === 0 ? (
        <div style={styles.empty}>
          {search || statusFilter || modeFilter ? 'No matching presentations' : 'No presentations yet'}
        </div>
      ) : (
        <div style={styles.list}>
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {(hasPrev || hasMore) && (
        <div style={styles.pagination}>
          <button
            disabled={!hasPrev}
            onClick={() => setOffset((p) => Math.max(0, p - limit))}
            style={{
              ...styles.pageBtn,
              opacity: hasPrev ? 1 : 0.3,
            }}
          >
            Previous
          </button>
          <span style={styles.pageInfo}>
            {offset + 1}–{Math.min(offset + limit, total)} of {total}
          </span>
          <button
            disabled={!hasMore}
            onClick={() => setOffset((p) => p + limit)}
            style={{
              ...styles.pageBtn,
              opacity: hasMore ? 1 : 0.3,
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    maxWidth: '800px',
    animation: 'fadeInUp 0.3s ease',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: '32px',
    color: 'var(--pr-charcoal)',
    marginBottom: '20px',
  },
  filters: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    marginBottom: '20px',
  },
  searchInput: {
    flex: 1,
    padding: '10px 14px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    fontSize: '14px',
    color: 'var(--pr-charcoal)',
    outline: 'none',
    fontFamily: 'var(--font-body)',
  },
  filterSelect: {
    padding: '10px 14px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    fontSize: '13px',
    color: 'var(--pr-charcoal)',
    cursor: 'pointer',
    outline: 'none',
    appearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23666666' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 10px center',
    paddingRight: '30px',
  },
  count: {
    fontSize: '13px',
    color: 'var(--pr-gray)',
    whiteSpace: 'nowrap',
  },
  countNum: {
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    color: 'var(--pr-teal)',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  loading: {
    padding: '48px 0',
    textAlign: 'center',
    color: 'var(--pr-gray)',
  },
  empty: {
    padding: '48px 0',
    textAlign: 'center',
    color: 'var(--pr-gray)',
    fontSize: '14px',
  },
  pagination: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    marginTop: '20px',
  },
  pageBtn: {
    padding: '8px 16px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
    cursor: 'pointer',
  },
  pageInfo: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--pr-gray)',
  },
};
