import type { CSSProperties } from 'react';
import { LANGUAGES } from '../types';

interface Props {
  label: string;
  value: string;
  onChange: (v: string) => void;
  excludeAuto?: boolean;
}

export default function LanguagePicker({ label, value, onChange, excludeAuto }: Props) {
  const options = excludeAuto ? LANGUAGES.filter((l) => l.code !== 'auto') : LANGUAGES;

  return (
    <div>
      <label style={styles.label}>{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={styles.select}
      >
        {options.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
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
