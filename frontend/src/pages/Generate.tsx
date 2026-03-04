import { useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { createJob } from '../api';
import type { GenerationMode } from '../types';
import FileDropzone from '../components/FileDropzone';
import ModeSelector from '../components/ModeSelector';
import PromptInput from '../components/PromptInput';
import LanguagePicker from '../components/LanguagePicker';
import BrandSelector from '../components/BrandSelector';

export default function Generate() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<GenerationMode>('ocr_editable');
  const [prompt, setPrompt] = useState('');
  const [language, setLanguage] = useState('auto');
  const [targetLang, setTargetLang] = useState('');
  const [slideCount, setSlideCount] = useState(8);
  const [brandKitId, setBrandKitId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

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
    background: 'rgba(194, 59, 34, 0.1)',
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
};
