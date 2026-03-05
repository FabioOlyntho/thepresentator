import { useState, useRef, useEffect, type CSSProperties } from 'react';

const SUGGESTIONS = [
  'Create a persuasive executive presentation',
  'Focus on ROI and business impact',
  'Design for a technical audience',
  'Make it visually engaging with data highlights',
];

interface Props {
  value: string;
  onChange: (v: string) => void;
}

export default function PromptInput({ value, onChange }: Props) {
  const [focused, setFocused] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = 'auto';
      ref.current.style.height = Math.max(80, ref.current.scrollHeight) + 'px';
    }
  }, [value]);

  return (
    <div>
      <label style={styles.label}>Prompt (optional)</label>
      <div style={{
        ...styles.wrapper,
        ...(focused ? styles.wrapperFocused : {}),
      }}>
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Describe your vision for this presentation..."
          style={styles.textarea}
          rows={3}
        />
      </div>
      {!value && (
        <div style={styles.chips}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onChange(s)}
              style={styles.chip}
            >
              {s}
            </button>
          ))}
        </div>
      )}
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
  wrapper: {
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    background: 'var(--pr-cream-warm)',
    transition: 'all 0.15s ease',
    overflow: 'hidden',
  },
  wrapperFocused: {
    borderColor: 'var(--pr-teal)',
    boxShadow: '0 0 0 3px rgba(15, 23, 42, 0.08)',
  },
  textarea: {
    width: '100%',
    padding: '12px 14px',
    border: 'none',
    background: 'transparent',
    resize: 'none',
    fontSize: '14px',
    lineHeight: 1.6,
    color: 'var(--pr-charcoal)',
    outline: 'none',
    fontFamily: 'var(--font-body)',
  },
  chips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    marginTop: '8px',
  },
  chip: {
    padding: '5px 12px',
    borderRadius: '20px',
    border: '1px solid var(--pr-beige)',
    background: 'var(--pr-cream)',
    fontSize: '12px',
    color: 'var(--pr-gray)',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
};
