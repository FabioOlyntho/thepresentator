import { useNavigate } from 'react-router-dom';
import type { CSSProperties } from 'react';
import type { Job } from '../types';
import { STATUS_COLORS } from '../types';

interface Props {
  job: Job;
}

export default function JobCard({ job }: Props) {
  const navigate = useNavigate();

  function formatTime(seconds: number | null): string {
    if (!seconds) return '—';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
  }

  function formatDate(iso: string): string {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const hours = diff / (1000 * 60 * 60);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${Math.floor(hours)}h ago`;
    if (hours < 48) return 'Yesterday';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  const modeLabels: Record<string, string> = {
    editable: 'Editable',
    full_slide: 'Full Slide',
    notebooklm: 'NotebookLM',
    ocr_editable: 'OCR+Edit',
    translate: 'Translate',
  };

  return (
    <button
      onClick={() => navigate(`/jobs/${job.id}`)}
      style={styles.card}
    >
      {/* Thumbnail preview */}
      <div style={styles.preview}>
        {job.slides.length > 0 && job.slides[0].thumbnail_url ? (
          <img
            src={`/api/v1/jobs/${job.id}/thumbnails/1`}
            alt={job.title ?? 'Presentation'}
            style={styles.previewImg}
          />
        ) : (
          <div style={styles.previewPlaceholder}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--pr-beige)" strokeWidth="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
        )}
      </div>

      {/* Info */}
      <div style={styles.info}>
        <div style={styles.title}>
          {job.title ?? job.input_filename}
        </div>
        <div style={styles.meta}>
          <span style={{
            ...styles.statusBadge,
            background: STATUS_COLORS[job.status] ?? 'var(--pr-gray)',
          }}>
            {job.status}
          </span>
          <span style={styles.metaText}>
            {modeLabels[job.mode] ?? job.mode}
          </span>
          <span style={styles.metaDot} />
          <span style={styles.metaText}>
            {job.slides.length > 0 ? `${job.slides.length} slides` : `${job.slide_count} target`}
          </span>
        </div>
        <div style={styles.footer}>
          <span style={styles.footerTime}>{formatDate(job.created_at)}</span>
          {job.time_total && (
            <span style={styles.footerDuration}>{formatTime(job.time_total)}</span>
          )}
          {job.pinned && <span style={styles.pin}>Pinned</span>}
        </div>
      </div>
    </button>
  );
}

const styles: Record<string, CSSProperties> = {
  card: {
    display: 'flex',
    gap: '14px',
    padding: '14px',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    textAlign: 'left',
    width: '100%',
  },
  preview: {
    width: '80px',
    height: '50px',
    borderRadius: 'var(--radius-sm)',
    overflow: 'hidden',
    flexShrink: 0,
    background: 'var(--pr-teal)',
  },
  previewImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  previewPlaceholder: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, var(--pr-teal) 0%, var(--pr-teal-light) 100%)',
  },
  info: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '4px',
  },
  statusBadge: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    fontWeight: 500,
    color: 'var(--pr-white)',
    padding: '1px 6px',
    borderRadius: '3px',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  },
  metaText: {
    fontSize: '12px',
    color: 'var(--pr-gray)',
  },
  metaDot: {
    width: '3px',
    height: '3px',
    borderRadius: '50%',
    background: 'var(--pr-beige)',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '4px',
  },
  footerTime: {
    fontSize: '11px',
    color: 'var(--pr-gray)',
  },
  footerDuration: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--pr-gray)',
  },
  pin: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--pr-red)',
    marginLeft: 'auto',
  },
};
