import type { CSSProperties } from 'react';
import type { BrandKit } from '../types';

interface Props {
  brand: BrandKit;
  onClick?: () => void;
  selected?: boolean;
}

export default function BrandKitCard({ brand, onClick, selected }: Props) {
  return (
    <button
      onClick={onClick}
      style={{
        ...styles.card,
        ...(selected ? styles.cardSelected : {}),
      }}
    >
      {/* Color swatches */}
      <div style={styles.swatches}>
        <div style={{ ...styles.swatch, background: brand.colors.primary }} />
        <div style={{ ...styles.swatch, background: brand.colors.secondary }} />
        <div style={{ ...styles.swatch, background: brand.colors.accent }} />
        <div style={{ ...styles.swatch, background: brand.colors.background, border: '1px solid var(--pr-beige)' }} />
      </div>

      <div style={styles.name}>{brand.name}</div>
      <div style={styles.meta}>
        <span style={styles.font}>{brand.fonts.title}</span>
        {brand.is_default && <span style={styles.default}>Default</span>}
      </div>
    </button>
  );
}

const styles: Record<string, CSSProperties> = {
  card: {
    padding: '16px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    textAlign: 'left',
    width: '100%',
  },
  cardSelected: {
    borderColor: 'var(--pr-teal)',
    boxShadow: 'var(--shadow-md)',
  },
  swatches: {
    display: 'flex',
    gap: '4px',
    marginBottom: '10px',
  },
  swatch: {
    width: '28px',
    height: '28px',
    borderRadius: '6px',
  },
  name: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--pr-charcoal)',
  },
  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '4px',
  },
  font: {
    fontSize: '12px',
    color: 'var(--pr-gray)',
  },
  default: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--pr-red)',
    textTransform: 'uppercase',
  },
};
