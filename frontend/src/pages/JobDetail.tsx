import { useState, useEffect, useRef, type CSSProperties } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getJob, deleteJob, togglePin, getDownloadUrl, connectJobWs } from '../api';
import type { Job, ProgressEvent } from '../types';
import ProgressTracker from '../components/ProgressTracker';
import SlideCarousel from '../components/SlideCarousel';

export default function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);

  // Fetch job
  useEffect(() => {
    if (!jobId) return;
    getJob(jobId).then(setJob).catch(() => navigate('/'));
  }, [jobId, navigate]);

  // WebSocket for progress
  useEffect(() => {
    if (!jobId || !job) return;
    if (job.status === 'completed' || job.status === 'failed') return;

    let mounted = true;

    const ws = connectJobWs(
      jobId,
      (event) => {
        if (!mounted) return;
        setEvents((prev) => [...prev, event]);
        if (event.step === 'completed' || event.step === 'failed') {
          getJob(jobId).then((j) => mounted && setJob(j));
        }
      },
      () => {
        setTimeout(() => {
          if (!mounted) return;
          getJob(jobId).then((j) => {
            if (!mounted) return;
            setJob(j);
          }).catch(() => {});
        }, 2000);
      }
    );
    wsRef.current = ws;

    return () => {
      mounted = false;
      ws.close();
    };
  }, [jobId, job?.status]);

  // Elapsed timer
  useEffect(() => {
    if (!job) return;
    if (job.status !== 'pending' && job.status !== 'processing') {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    const start = new Date(job.created_at).getTime();
    timerRef.current = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [job?.status, job?.created_at]);

  async function handleDelete() {
    if (!jobId) return;
    if (!window.confirm('Delete this presentation?')) return;
    await deleteJob(jobId);
    navigate('/history');
  }

  async function handlePin() {
    if (!jobId || !job) return;
    const result = await togglePin(jobId);
    setJob({ ...job, pinned: result.pinned });
  }

  function formatElapsed(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec.toString().padStart(2, '0')}s`;
  }

  function formatTime(s: number | null): string {
    if (!s) return '—';
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${m}m ${sec}s`;
  }

  if (!job) {
    return <div style={styles.loading}>Loading...</div>;
  }

  const isActive = job.status === 'pending' || job.status === 'processing';
  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';

  const modeLabels: Record<string, string> = {
    editable: 'Editable',
    full_slide: 'Full Slide',
    notebooklm: 'NotebookLM',
    ocr_editable: 'OCR + Editable',
    translate: 'Translate',
  };

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>
            {job.title ?? job.input_filename}
          </h1>
          <div style={styles.meta}>
            <span style={styles.modeBadge}>{modeLabels[job.mode] ?? job.mode}</span>
            {job.language && <span style={styles.metaText}>Language: {job.language}</span>}
            {job.slides.length > 0 && (
              <span style={styles.metaText}>{job.slides.length} slides</span>
            )}
            {isActive && (
              <span style={styles.elapsed}>{formatElapsed(elapsed)}</span>
            )}
            {isCompleted && job.time_total && (
              <span style={styles.elapsed}>{formatTime(job.time_total)}</span>
            )}
          </div>
        </div>
        <div style={styles.headerActions}>
          {isCompleted && (
            <a href={getDownloadUrl(job.id)} style={styles.downloadBtn}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download PPTX
            </a>
          )}
          <button onClick={handlePin} style={styles.iconBtn} title={job.pinned ? 'Unpin' : 'Pin'}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill={job.pinned ? 'var(--pr-red)' : 'none'} stroke={job.pinned ? 'var(--pr-red)' : 'currentColor'} strokeWidth="1.8">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          </button>
          <button onClick={handleDelete} style={styles.iconBtn} title="Delete">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--pr-error)" strokeWidth="1.8">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Progress (active jobs) */}
      {isActive && (
        <div style={styles.progressSection}>
          <ProgressTracker events={events} status={job.status} />
        </div>
      )}

      {/* Error */}
      {isFailed && (
        <div style={styles.errorBox}>
          <div style={styles.errorTitle}>Generation Failed</div>
          <div style={styles.errorMsg}>{job.error_message ?? 'An unknown error occurred'}</div>
        </div>
      )}

      {/* Slide Preview (completed jobs) */}
      {isCompleted && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Slides</h2>
          <SlideCarousel slides={job.slides} jobId={job.id} />
        </div>
      )}

      {/* Details */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Details</h2>
        <div style={styles.details}>
          <DetailRow label="Mode" value={modeLabels[job.mode] ?? job.mode} />
          <DetailRow label="Input" value={job.input_filename} />
          <DetailRow label="Language" value={job.language ?? 'Auto'} />
          {job.target_language && <DetailRow label="Translate To" value={job.target_language} />}
          {job.prompt && <DetailRow label="Prompt" value={job.prompt} />}
          <DetailRow label="Slide Count" value={String(job.slide_count)} mono />
          <DetailRow label="Created" value={new Date(job.created_at).toLocaleString()} />
          {job.time_total && <DetailRow label="Duration" value={formatTime(job.time_total)} mono />}
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={detailStyles.row}>
      <span style={detailStyles.label}>{label}</span>
      <span style={{
        ...detailStyles.value,
        ...(mono ? { fontFamily: 'var(--font-mono)' } : {}),
      }}>
        {value}
      </span>
    </div>
  );
}

const detailStyles: Record<string, CSSProperties> = {
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '8px 0',
    borderBottom: '1px solid rgba(194, 191, 170, 0.3)',
  },
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--pr-gray)',
  },
  value: {
    fontSize: '13px',
    color: 'var(--pr-charcoal)',
    textAlign: 'right',
    maxWidth: '60%',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
};

const styles: Record<string, CSSProperties> = {
  page: {
    maxWidth: '800px',
    animation: 'fadeInUp 0.3s ease',
  },
  loading: {
    padding: '60px 0',
    textAlign: 'center',
    color: 'var(--pr-gray)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '28px',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: '28px',
    color: 'var(--pr-charcoal)',
    lineHeight: 1.2,
  },
  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginTop: '6px',
  },
  modeBadge: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--pr-teal)',
    background: 'rgba(1, 38, 45, 0.08)',
    padding: '2px 8px',
    borderRadius: '4px',
    textTransform: 'uppercase',
  },
  metaText: {
    fontSize: '13px',
    color: 'var(--pr-gray)',
  },
  elapsed: {
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    color: 'var(--pr-teal)',
    fontWeight: 500,
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  downloadBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--pr-red)',
    color: 'var(--pr-white)',
    fontSize: '14px',
    fontWeight: 600,
    textDecoration: 'none',
    transition: 'all 0.15s ease',
  },
  iconBtn: {
    padding: '8px',
    borderRadius: 'var(--radius-sm)',
    color: 'var(--pr-gray)',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  progressSection: {
    padding: '28px 24px',
    borderRadius: 'var(--radius-lg)',
    background: 'var(--pr-cream-warm)',
    border: '1px solid var(--pr-beige)',
    marginBottom: '24px',
  },
  errorBox: {
    padding: '20px 24px',
    borderRadius: 'var(--radius-md)',
    background: 'rgba(194, 59, 34, 0.06)',
    border: '1px solid var(--pr-error)',
    marginBottom: '24px',
  },
  errorTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--pr-error)',
    marginBottom: '4px',
  },
  errorMsg: {
    fontSize: '13px',
    color: 'var(--pr-charcoal)',
    lineHeight: 1.5,
  },
  section: {
    marginBottom: '24px',
  },
  sectionTitle: {
    fontFamily: 'var(--font-display)',
    fontSize: '20px',
    color: 'var(--pr-charcoal)',
    marginBottom: '14px',
  },
  details: {
    padding: '16px 20px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--pr-cream-warm)',
    border: '1px solid var(--pr-beige)',
  },
};
