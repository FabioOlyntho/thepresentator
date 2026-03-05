import type { CSSProperties } from 'react';

type PdnobLevel = 'ocr_only' | 'remove_bg' | 'full';

interface Props {
  value: PdnobLevel;
  onChange: (level: PdnobLevel) => void;
}

const LEVEL_OPTIONS: { id: PdnobLevel; label: string; description: string; recommended?: boolean }[] = [
  {
    id: 'ocr_only',
    label: 'OCR Only',
    description: 'Keep original image as background, add editable text boxes on top',
  },
  {
    id: 'remove_bg',
    label: 'Remove Background',
    description: 'Cut out each illustration and remove the background. No text boxes.',
  },
  {
    id: 'full',
    label: 'Full',
    description: 'Both: cut out illustrations without background + editable text boxes',
    recommended: true,
  },
];

export default function PdnobLevelSelector({ value, onChange }: Props) {
  return (
    <div style={styles.wrapper}>
      <label style={styles.label}>PDNob Level</label>
      <div style={styles.grid}>
        {LEVEL_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => onChange(opt.id)}
            style={{
              ...styles.card,
              ...(value === opt.id ? styles.cardActive : {}),
            }}
          >
            <div style={styles.cardTop}>
              {opt.recommended && <span style={styles.recommended}>Recommended</span>}
            </div>
            <div style={{
              ...styles.cardLabel,
              ...(value === opt.id ? styles.cardLabelActive : {}),
            }}>
              {opt.label}
            </div>
            <div style={styles.cardDesc}>{opt.description}</div>
            {value === opt.id && <div style={styles.checkmark}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--pr-red)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>}
          </button>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  wrapper: {
    marginTop: '4px',
  },
  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--pr-gray)',
    marginBottom: '6px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '8px',
  },
  card: {
    position: 'relative',
    padding: '10px 12px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    textAlign: 'left',
    transition: 'all 0.15s ease',
    cursor: 'pointer',
  },
  cardActive: {
    borderColor: 'var(--pr-teal)',
    background: 'var(--pr-white)',
    boxShadow: 'var(--shadow-md)',
  },
  cardTop: {
    minHeight: '16px',
    marginBottom: '2px',
  },
  recommended: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    fontWeight: 500,
    color: 'var(--pr-red)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  },
  cardLabel: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--pr-charcoal)',
    marginBottom: '3px',
  },
  cardLabelActive: {
    color: 'var(--pr-teal)',
  },
  cardDesc: {
    fontSize: '11px',
    color: 'var(--pr-gray)',
    lineHeight: 1.4,
  },
  checkmark: {
    position: 'absolute',
    top: '8px',
    right: '8px',
  },
};
