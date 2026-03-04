import { useState, useEffect, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { listJobs } from '../api';
import type { Job } from '../types';
import StatsBar from '../components/StatsBar';
import JobCard from '../components/JobCard';

export default function Dashboard() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listJobs({ limit: 6 })
      .then((res) => setJobs(res.jobs))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalJobs = jobs.length;
  const completed = jobs.filter((j) => j.status === 'completed').length;
  const totalSlides = jobs.reduce((sum, j) => sum + j.slides.length, 0);

  return (
    <div style={styles.page}>
      {/* Hero */}
      <div style={styles.hero}>
        <div style={styles.heroPattern} />
        <div style={styles.heroContent}>
          <h1 style={styles.heroTitle}>The Presentator</h1>
          <p style={styles.heroSub}>
            Transform any document into a stunning presentation with AI
          </p>
        </div>
        <div style={styles.heroAccent} />
      </div>

      {/* Quick Actions */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>Quick Actions</h2>
        <div style={styles.actions}>
          {QUICK_ACTIONS.map((action, i) => (
            <button
              key={action.label}
              onClick={() => navigate(action.to)}
              style={styles.actionCard}
              className={`stagger-${i + 1}`}
            >
              <div style={styles.actionIcon}>{action.icon}</div>
              <div style={styles.actionLabel}>{action.label}</div>
              <div style={styles.actionDesc}>{action.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      {!loading && totalJobs > 0 && (
        <StatsBar
          stats={[
            { label: 'Presentations', value: totalJobs },
            { label: 'Completed', value: completed },
            { label: 'Total Slides', value: totalSlides },
          ]}
        />
      )}

      {/* Recent */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>Recent Presentations</h2>
          {jobs.length > 0 && (
            <button onClick={() => navigate('/history')} style={styles.viewAll}>
              View All
            </button>
          )}
        </div>
        {loading ? (
          <div style={styles.loading}>Loading...</div>
        ) : jobs.length === 0 ? (
          <div style={styles.empty}>
            <div style={styles.emptyIcon}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--pr-beige)" strokeWidth="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
            </div>
            <div style={styles.emptyText}>No presentations yet</div>
            <button onClick={() => navigate('/generate')} style={styles.emptyBtn}>
              Create your first
            </button>
          </div>
        ) : (
          <div style={styles.jobList}>
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const QUICK_ACTIONS = [
  {
    label: 'Create',
    desc: 'Generate from any document',
    to: '/generate',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--pr-teal)" strokeWidth="1.5">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
  },
  {
    label: 'Translate',
    desc: 'Translate existing PPTX',
    to: '/translate',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--pr-teal)" strokeWidth="1.5">
        <path d="M5 8l6 6" />
        <path d="M4 14l6-6 2-3" />
        <path d="M2 5h12" />
        <path d="M7 2v3" />
        <path d="M22 22l-5-10-5 10" />
        <path d="M14 18h6" />
      </svg>
    ),
  },
  {
    label: 'Brand Kits',
    desc: 'Custom branding presets',
    to: '/brands',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--pr-teal)" strokeWidth="1.5">
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </svg>
    ),
  },
];

const styles: Record<string, CSSProperties> = {
  page: {
    maxWidth: '900px',
    display: 'flex',
    flexDirection: 'column',
    gap: '28px',
  },
  hero: {
    position: 'relative',
    background: 'var(--pr-teal)',
    borderRadius: 'var(--radius-lg)',
    padding: '48px 40px',
    overflow: 'hidden',
    animation: 'fadeInUp 0.4s ease',
  },
  heroPattern: {
    position: 'absolute',
    inset: 0,
    opacity: 0.03,
    backgroundImage: `repeating-linear-gradient(
      45deg,
      transparent,
      transparent 30px,
      rgba(255,255,255,0.15) 30px,
      rgba(255,255,255,0.15) 31px
    )`,
    pointerEvents: 'none',
  },
  heroContent: {
    position: 'relative',
    zIndex: 1,
  },
  heroTitle: {
    fontFamily: 'var(--font-display)',
    fontSize: '42px',
    color: 'var(--pr-cream)',
    lineHeight: 1.1,
    marginBottom: '8px',
  },
  heroSub: {
    fontSize: '16px',
    color: 'var(--pr-beige)',
    fontWeight: 300,
    maxWidth: '400px',
  },
  heroAccent: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '4px',
    background: 'var(--pr-red)',
  },
  section: {
    animation: 'fadeInUp 0.4s ease both',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '14px',
  },
  sectionTitle: {
    fontFamily: 'var(--font-display)',
    fontSize: '22px',
    color: 'var(--pr-charcoal)',
    marginBottom: '14px',
  },
  viewAll: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--pr-red)',
    cursor: 'pointer',
    marginBottom: '14px',
  },
  actions: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '14px',
  },
  actionCard: {
    padding: '24px 20px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    textAlign: 'left',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    animation: 'fadeInUp 0.3s ease both',
  },
  actionIcon: {
    marginBottom: '12px',
  },
  actionLabel: {
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--pr-charcoal)',
    marginBottom: '4px',
  },
  actionDesc: {
    fontSize: '13px',
    color: 'var(--pr-gray)',
  },
  jobList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  loading: {
    padding: '40px 0',
    textAlign: 'center',
    color: 'var(--pr-gray)',
    fontSize: '14px',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    padding: '48px 0',
  },
  emptyIcon: {
    opacity: 0.5,
  },
  emptyText: {
    fontSize: '14px',
    color: 'var(--pr-gray)',
  },
  emptyBtn: {
    padding: '10px 24px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--pr-red)',
    color: 'var(--pr-white)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
};
