import { useState, useEffect, type CSSProperties } from 'react';
import { listBrands } from '../api';
import type { BrandKit } from '../types';

interface Props {
  value: string | null;
  onChange: (id: string | null) => void;
}

export default function BrandSelector({ value, onChange }: Props) {
  const [brands, setBrands] = useState<BrandKit[]>([]);

  useEffect(() => {
    listBrands().then(setBrands).catch(() => {});
  }, []);

  return (
    <div>
      <label style={styles.label}>Brand Kit</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        style={styles.select}
      >
        <option value="">Recodme (default)</option>
        {brands.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}{b.is_default ? ' (default)' : ''}
          </option>
        ))}
      </select>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
    marginBottom: '6px',
  },
  select: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    fontSize: '14px',
    color: 'var(--pr-charcoal)',
    cursor: 'pointer',
    outline: 'none',
    appearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23666666' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 12px center',
    paddingRight: '36px',
  },
};
