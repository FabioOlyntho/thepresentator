import { useState, useEffect, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { createJob, nlmAuthStatus } from '../api';
import type { GenerationMode } from '../types';
import FileDropzone from '../components/FileDropzone';
import ModeSelector from '../components/ModeSelector';
import PdnobLevelSelector from '../components/PdnobLevelSelector';
import PromptInput from '../components/PromptInput';
import LanguagePicker from '../components/LanguagePicker';
import BrandSelector from '../components/BrandSelector';

const NLM_MODES = new Set(['notebooklm', 'ocr_editable', 'full_slide', 'pdnob']);

export default function Generate() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<GenerationMode>('ocr_editable');
  const [prompt, setPrompt] = useState('');
  const [language, setLanguage] = useState('auto');
  const [targetLang, setTargetLang] = useState('');
  const [slideCount, setSlideCount] = useState(8);
  const [brandKitId, setBrandKitId] = useState<string | null>(null);
  const [pdnobLevel, setPdnobLevel] = useState<'ocr_only' | 'remove_bg' | 'full'>('full');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [nlmAuth, setNlmAuth] = useState<boolean | null>(null);

  // Check NLM auth status on mount and when mode changes
  useEffect(() => {
    if (NLM_MODES.has(mode)) {
      nlmAuthStatus()
        .then(({ authenticated }) => setNlmAuth(authenticated))
        .catch(() => setNlmAuth(null));
    }
  }, [mode]);

  async function handleGenerate() {
    if (!file) return;
    setSubmitting(true);
    setError('');

    try {
      const options: Record<string, unknown> = {
        mode,
        slide_count: slideCount,
      };
      if (prompt) options.prompt = prompt;
      if (language !== 'auto') options.language = language;
      if (targetLang) options.target_language = targetLang;
      if (brandKitId) options.brand_kit_id = brandKitId;
      if (mode === 'pdnob') options.pdnob_level = pdnobLevel;

      const job = await createJob(file, options);
      navigate(`/jobs/${job.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create job';
      setError(msg);
      setSubmitting(false);
    }
  }

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>Create Presentation</h1>

      <div style={styles.layout}>
        {/* Left: File Upload */}
        <div style={styles.left}>
          <FileDropzone file={file} onFile={setFile} />

          <PromptInput value={prompt} onChange={setPrompt} />
        </div>

        {/* Right: Options */}
        <div style={styles.right}>
          <div>
            <label style={styles.label}>Generation Mode</label>
            <ModeSelector value={mode} onChange={setMode} />
            {mode === 'pdnob' && (
              <PdnobLevelSelector value={pdnobLevel} onChange={setPdnobLevel} />
            )}
          </div>

          <LanguagePicker
            label="Source Language"
            value={language}
            onChange={setLanguage}
          />

          <LanguagePicker
            label="Translate To (optional)"
            value={targetLang}
            onChange={setTargetLang}
            excludeAuto
          />

          <div>
            <label style={styles.label}>
              Slide Count: <span style={styles.sliderValue}>{slideCount}</span>
            </label>
            <input
              type="range"
              min={4}
              max={20}
              value={slideCount}
              onChange={(e) => setSlideCount(Number(e.target.value))}
              style={styles.slider}
            />
            <div style={styles.sliderLabels}>
              <span>4</span>
              <span>20</span>
            </div>
          </div>

          <BrandSelector value={brandKitId} onChange={setBrandKitId} />
        </div>
      </div>

      {NLM_MODES.has(mode) && nlmAuth === false && (
        <div style={styles.authBanner}>
          <div style={styles.authIcon}>!</div>
          <div>
            <strong>NotebookLM not authenticated</strong>
            <p style={styles.authText}>
              Run this command on your computer to sign in:
            </p>
            <code style={styles.authCode}>
              .\venv\Scripts\python.exe scripts\auth_local.py
            </code>
            <p style={styles.authNote}>
              A Chrome window will open for Google sign-in. After login, cookies
              are uploaded to the server automatically. You can still generate
              without auth — it will use Editable mode as fallback.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div style={styles.error}>{error}</div>
      )}

      <button
        onClick={handleGenerate}
        disabled={!file || submitting}
        style={{
          ...styles.generateBtn,
          opacity: !file || submitting ? 0.5 : 1,
        }}
      >
        {submitting ? (
          <span style={styles.spinnerWrap}>
            <span style={styles.spinner} />
            Creating...
          </span>
        ) : (
          'Generate Presentation'
        )}
      </button>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    maxWidth: '960px',
    animation: 'fadeInUp 0.3s ease',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: '32px',
    color: 'var(--pr-charcoal)',
    marginBottom: '24px',
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '1.2fr 1fr',
    gap: '28px',
    marginBottom: '24px',
  },
  left: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  right: {
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
    marginBottom: '8px',
  },
  sliderValue: {
    fontFamily: 'var(--font-mono)',
    color: 'var(--pr-teal)',
    fontWeight: 600,
  },
  slider: {
    width: '100%',
    accentColor: 'var(--pr-teal)',
  },
  sliderLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
    color: 'var(--pr-gray)',
    marginTop: '2px',
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
  generateBtn: {
    width: '100%',
    padding: '16px 24px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--pr-red)',
    color: 'var(--pr-white)',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    border: 'none',
    fontFamily: 'var(--font-body)',
  },
  spinnerWrap: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
  },
  spinner: {
    width: '16px',
    height: '16px',
    border: '2px solid rgba(255,255,255,0.3)',
    borderTopColor: 'white',
    borderRadius: '50%',
    animation: 'spin 0.6s linear infinite',
    display: 'inline-block',
  },
  authBanner: {
    display: 'flex',
    gap: '14px',
    padding: '16px 20px',
    borderRadius: 'var(--radius-md)',
    background: 'rgba(245, 158, 11, 0.08)',
    border: '1px solid rgba(245, 158, 11, 0.3)',
    marginBottom: '16px',
    alignItems: 'flex-start',
  },
  authIcon: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    background: 'rgba(245, 158, 11, 0.15)',
    color: '#D97706',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    fontSize: '15px',
    flexShrink: 0,
    marginTop: '2px',
  },
  authText: {
    fontSize: '13px',
    color: 'var(--pr-gray)',
    margin: '6px 0 8px',
  },
  authCode: {
    display: 'block',
    padding: '10px 14px',
    borderRadius: '6px',
    background: 'var(--pr-charcoal)',
    color: '#E2E8F0',
    fontSize: '13px',
    fontFamily: 'var(--font-mono)',
    userSelect: 'all' as const,
    cursor: 'text',
  },
  authNote: {
    fontSize: '12px',
    color: 'var(--pr-gray)',
    margin: '8px 0 0',
    opacity: 0.7,
    lineHeight: 1.5,
  },
};
