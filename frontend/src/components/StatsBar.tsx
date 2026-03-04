import type { CSSProperties } from 'react';

interface Stat {
  label: string;
  value: string | number;
  mono?: boolean;
}

interface Props {
  stats: Stat[];
}

export default function StatsBar({ stats }: Props) {
  return (
    <div style={styles.bar}>
      {stats.map((stat, i) => (
        <div key={i} style={styles.item}>
          <div style={{
            ...styles.value,
            ...(stat.mono ? { fontFamily: 'var(--font-mono)' } : {}),
          }}>
            {stat.value}
          </div>
          <div style={styles.label}>{stat.label}</div>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  bar: {
    display: 'flex',
    gap: '32px',
    padding: '20px 24px',
    borderRadius: 'var(--radius-md)',
    background: 'var(--pr-cream-warm)',
    border: '1px solid var(--pr-beige)',
  },
  item: {
    textAlign: 'center',
  },
  value: {
    fontFamily: 'var(--font-display)',
    fontSize: '28px',
    color: 'var(--pr-teal)',
    lineHeight: 1.2,
  },
  label: {
    fontSize: '12px',
    color: 'var(--pr-gray)',
    marginTop: '2px',
  },
};
