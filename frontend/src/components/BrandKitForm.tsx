import { useState, type CSSProperties, type FormEvent } from 'react';
import type { BrandColors, BrandFonts } from '../types';

interface Props {
  initial?: {
    name: string;
    colors: BrandColors;
    fonts: BrandFonts;
    logo_position: string;
  };
  onSubmit: (data: {
    name: string;
    colors: BrandColors;
    fonts: BrandFonts;
    logo_position: string;
  }) => void;
  onCancel: () => void;
  loading?: boolean;
}

const DEFAULT_COLORS: BrandColors = {
  primary: '#01262D',
  secondary: '#313131',
  accent: '#E84422',
  background: '#F5F0E8',
  text_dark: '#313131',
  text_light: '#FFFFFF',
  highlight: '#E84422',
};

const DEFAULT_FONTS: BrandFonts = {
  title: 'Poppins',
  body: 'Poppins',
  accent: 'Poppins Light',
};

const COLOR_LABELS: Record<keyof BrandColors, string> = {
  primary: 'Primary',
  secondary: 'Secondary',
  accent: 'Accent',
  background: 'Background',
  text_dark: 'Text Dark',
  text_light: 'Text Light',
  highlight: 'Highlight',
};

const LOGO_POSITIONS = [
  { value: 'title_and_footer', label: 'Title & Footer' },
  { value: 'title_only', label: 'Title Only' },
  { value: 'footer_only', label: 'Footer Only' },
  { value: 'watermark', label: 'Watermark' },
];

export default function BrandKitForm({ initial, onSubmit, onCancel, loading }: Props) {
  const [name, setName] = useState(initial?.name ?? '');
  const [colors, setColors] = useState<BrandColors>(initial?.colors ?? DEFAULT_COLORS);
  const [fonts, setFonts] = useState<BrandFonts>(initial?.fonts ?? DEFAULT_FONTS);
  const [logoPosition, setLogoPosition] = useState(initial?.logo_position ?? 'title_and_footer');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ name, colors, fonts, logo_position: logoPosition });
  }

  function updateColor(key: keyof BrandColors, value: string) {
    setColors((prev) => ({ ...prev, [key]: value }));
  }

  function updateFont(key: keyof BrandFonts, value: string) {
    setFonts((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      {/* Name */}
      <div>
        <label style={styles.label}>Brand Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. IESE Business School"
          style={styles.input}
          required
        />
      </div>

      {/* Colors */}
      <div>
        <label style={styles.label}>Colors</label>
        <div style={styles.colorGrid}>
          {(Object.keys(COLOR_LABELS) as (keyof BrandColors)[]).map((key) => (
            <div key={key} style={styles.colorItem}>
              <input
                type="color"
                value={colors[key]}
                onChange={(e) => updateColor(key, e.target.value)}
                style={styles.colorInput}
              />
              <span style={styles.colorLabel}>{COLOR_LABELS[key]}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Fonts */}
      <div>
        <label style={styles.label}>Fonts</label>
        <div style={styles.fontGrid}>
          {(['title', 'body', 'accent'] as (keyof BrandFonts)[]).map((key) => (
            <div key={key}>
              <label style={styles.subLabel}>{key.charAt(0).toUpperCase() + key.slice(1)}</label>
              <input
                value={fonts[key]}
                onChange={(e) => updateFont(key, e.target.value)}
                style={styles.input}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Logo Position */}
      <div>
        <label style={styles.label}>Logo Position</label>
        <select
          value={logoPosition}
          onChange={(e) => setLogoPosition(e.target.value)}
          style={styles.select}
        >
          {LOGO_POSITIONS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* Actions */}
      <div style={styles.actions}>
        <button type="button" onClick={onCancel} style={styles.cancelBtn}>
          Cancel
        </button>
        <button type="submit" disabled={loading || !name.trim()} style={styles.submitBtn}>
          {loading ? 'Saving...' : initial ? 'Update' : 'Create'}
        </button>
      </div>
    </form>
  );
}

const styles: Record<string, CSSProperties> = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--pr-charcoal)',
    marginBottom: '8px',
  },
  subLabel: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--pr-gray)',
    marginBottom: '4px',
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    fontSize: '14px',
    color: 'var(--pr-charcoal)',
    outline: 'none',
    fontFamily: 'var(--font-body)',
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
  colorGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '10px',
  },
  colorItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
  },
  colorInput: {
    width: '40px',
    height: '40px',
    borderRadius: '8px',
    border: '2px solid var(--pr-beige)',
    cursor: 'pointer',
    padding: 0,
    background: 'none',
  },
  colorLabel: {
    fontSize: '10px',
    color: 'var(--pr-gray)',
    textAlign: 'center',
  },
  fontGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '10px',
  },
  actions: {
    display: 'flex',
    gap: '10px',
    justifyContent: 'flex-end',
    paddingTop: '8px',
    borderTop: '1px solid var(--pr-beige)',
  },
  cancelBtn: {
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream)',
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--pr-gray)',
    cursor: 'pointer',
  },
  submitBtn: {
    padding: '10px 24px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    background: 'var(--pr-red)',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--pr-white)',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
};
