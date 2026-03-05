import { useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { createJob } from '../api';
import FileDropzone from '../components/FileDropzone';
import LanguagePicker from '../components/LanguagePicker';

export default function Translate() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [sourceLang, setSourceLang] = useState('ES');
  const [targetLang, setTargetLang] = useState('EN');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleTranslate() {
    if (!file) return;
    setSubmitting(true);
    setError('');

    try {
      const job = await createJob(file, {
        mode: 'translate',
        language: sourceLang,
        target_language: targetLang,
      });
      navigate(`/jobs/${job.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start translation';
      setError(msg);
      setSubmitting(false);
    }
  }

  const isPptx = file?.name.endsWith('.pptx');

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>Translate Presentation</h1>
      <p style={styles.subtitle}>
        Upload a PPTX file and translate it while preserving layout and formatting
      </p>

      <div style={styles.layout}>
        <div style={styles.left}>
          <FileDropzone file={file} onFile={setFile} />
          {file && !isPptx && (
            <div style={styles.warning}>
              Translation works best with PPTX files. Other formats will generate a new presentation in the target language.
            </div>
          )}
        </div>

        <div style={styles.right}>
          <div style={styles.langRow}>
            <div style={styles.langCol}>
              <LanguagePicker
                label="From"
                value={sourceLang}
                onChange={setSourceLang}
                excludeAuto
              />
            </div>

            <div style={styles.arrow}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--pr-teal)" strokeWidth="2" strokeLinecap="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </div>

            <div style={styles.langCol}>
              <LanguagePicker
                label="To"
                value={targetLang}
                onChange={setTargetLang}
                excludeAuto
              />
            </div>
          </div>

          <div style={styles.infoBox}>
            <div style={styles.infoTitle}>How translation works</div>
            <ul style={styles.infoList}>
              <li>Text is extracted from all slide shapes</li>
              <li>Batch-translated via Gemini AI for context accuracy</li>
              <li>Replaced in-place preserving fonts, colors, and positions</li>
              <li>Layout and images remain unchanged</li>
            </ul>
          </div>
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <button
        onClick={handleTranslate}
        disabled={!file || submitting || sourceLang === targetLang}
        style={{
          ...styles.translateBtn,
          opacity: !file || submitting || sourceLang === targetLang ? 0.5 : 1,
        }}
      >
        {submitting ? 'Translating...' : `Translate ${sourceLang} → ${targetLang}`}
      </button>
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
    marginBottom: '4px',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--pr-gray)',
    marginBottom: '28px',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '28px',
    marginBottom: '24px',
  },
  left: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  right: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  langRow: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '12px',
  },
  langCol: {
    flex: 1,
  },
  arrow: {
    paddingBottom: '8px',
  },
  infoBox: {
    padding: '16px 20px',
    borderRadius: 'var(--radius-md)',
    background: 'rgba(15, 23, 42, 0.04)',
    border: '1px solid var(--pr-beige)',
  },
  infoTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--pr-teal)',
    marginBottom: '8px',
  },
  infoList: {
    listStyle: 'none',
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    fontSize: '12px',
    color: 'var(--pr-gray)',
    lineHeight: 1.5,
  },
  warning: {
    padding: '10px 14px',
    borderRadius: 'var(--radius-sm)',
    background: 'rgba(212, 160, 23, 0.1)',
    border: '1px solid var(--pr-warning)',
    fontSize: '12px',
    color: 'var(--pr-charcoal)',
  },
  error: {
    padding: '12px 16px',
    borderRadius: 'var(--radius-md)',
    background: 'rgba(220, 38, 38, 0.1)',
    border: '1px solid var(--pr-error)',
    color: 'var(--pr-error)',
    fontSize: '13px',
    marginBottom: '16px',
  },
  translateBtn: {
    width: '100%',
    padding: '16px 24px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--pr-teal)',
    color: 'var(--pr-white)',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    border: 'none',
    fontFamily: 'var(--font-body)',
  },
};
