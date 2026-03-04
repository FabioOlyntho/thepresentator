import type { CSSProperties } from 'react';
import { MODE_OPTIONS, type GenerationMode } from '../types';

interface Props {
  value: GenerationMode;
  onChange: (mode: GenerationMode) => void;
}

export default function ModeSelector({ value, onChange }: Props) {
  return (
    <div style={styles.grid}>
      {MODE_OPTIONS.map((opt) => (
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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--pr-red)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>}
        </button>
      ))}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
  },
  card: {
    position: 'relative',
    padding: '14px 16px',
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
    minHeight: '18px',
    marginBottom: '4px',
  },
  recommended: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    fontWeight: 500,
    color: 'var(--pr-red)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  cardLabel: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--pr-charcoal)',
    marginBottom: '4px',
  },
  cardLabelActive: {
    color: 'var(--pr-teal)',
  },
  cardDesc: {
    fontSize: '12px',
    color: 'var(--pr-gray)',
    lineHeight: 1.4,
  },
  checkmark: {
    position: 'absolute',
    top: '12px',
    right: '12px',
  },
};
