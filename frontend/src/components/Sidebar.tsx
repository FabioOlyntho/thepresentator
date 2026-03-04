import { NavLink } from 'react-router-dom';
import type { CSSProperties } from 'react';

const NAV_ITEMS: { to: string; label: string; icon: () => React.ReactNode }[] = [
  { to: '/', label: 'Home', icon: HomeIcon },
  { to: '/generate', label: 'Create', icon: CreateIcon },
  { to: '/translate', label: 'Translate', icon: TranslateIcon },
  { to: '/brands', label: 'Brand Kits', icon: BrandIcon },
  { to: '/history', label: 'History', icon: HistoryIcon },
];

export default function Sidebar() {
  return (
    <aside style={styles.sidebar}>
      {/* Geometric pattern overlay */}
      <div style={styles.pattern} />

      {/* Logo area */}
      <div style={styles.logoArea}>
        <div style={styles.logoMark}>P</div>
        <div>
          <div style={styles.logoTitle}>The Presentator</div>
          <div style={styles.logoSub}>Presentation Studio</div>
        </div>
      </div>

      {/* Red accent bar */}
      <div style={styles.accentBar} />

      {/* Navigation */}
      <nav style={styles.nav}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            style={({ isActive }) => ({
              ...styles.navItem,
              ...(isActive ? styles.navItemActive : {}),
            })}
          >
            <item.icon />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.footerText}>Powered by Gemini AI</div>
        <div style={styles.footerVersion}>v5.0</div>
      </div>
    </aside>
  );
}

/* ─── Icons (SVG inline) ─── */

function HomeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function CreateIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}

function TranslateIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 8l6 6" />
      <path d="M4 14l6-6 2-3" />
      <path d="M2 5h12" />
      <path d="M7 2v3" />
      <path d="M22 22l-5-10-5 10" />
      <path d="M14 18h6" />
    </svg>
  );
}

function BrandIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

/* ─── Styles ─── */

const styles: Record<string, CSSProperties> = {
  sidebar: {
    position: 'fixed',
    top: 0,
    left: 0,
    bottom: 0,
    width: 'var(--sidebar-width)',
    background: 'var(--pr-teal)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 100,
    overflow: 'hidden',
  },
  pattern: {
    position: 'absolute',
    inset: 0,
    opacity: 0.02,
    backgroundImage: `repeating-linear-gradient(
      45deg,
      transparent,
      transparent 20px,
      rgba(255,255,255,0.1) 20px,
      rgba(255,255,255,0.1) 21px
    )`,
    pointerEvents: 'none',
  },
  logoArea: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '28px 24px 20px',
    position: 'relative',
    zIndex: 1,
  },
  logoMark: {
    width: '40px',
    height: '40px',
    borderRadius: '10px',
    background: 'var(--pr-red)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--font-display)',
    fontSize: '22px',
    color: 'var(--pr-white)',
    flexShrink: 0,
  },
  logoTitle: {
    fontFamily: 'var(--font-display)',
    fontSize: '18px',
    color: 'var(--pr-white)',
    lineHeight: 1.2,
  },
  logoSub: {
    fontFamily: 'var(--font-body)',
    fontSize: '11px',
    color: 'var(--pr-beige)',
    fontWeight: 300,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
  },
  accentBar: {
    height: '3px',
    background: 'var(--pr-red)',
    margin: '0 24px 8px',
    borderRadius: '2px',
    position: 'relative',
    zIndex: 1,
  },
  nav: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    padding: '16px 12px',
    position: 'relative',
    zIndex: 1,
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '10px 16px',
    borderRadius: '8px',
    color: 'var(--pr-beige)',
    fontSize: '14px',
    fontWeight: 400,
    transition: 'all 0.15s ease',
    textDecoration: 'none',
  },
  navItemActive: {
    background: 'var(--pr-teal-light)',
    color: 'var(--pr-white)',
    fontWeight: 500,
  },
  footer: {
    padding: '16px 24px 24px',
    position: 'relative',
    zIndex: 1,
  },
  footerText: {
    fontSize: '11px',
    color: 'var(--pr-beige)',
    opacity: 0.6,
  },
  footerVersion: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--pr-beige)',
    opacity: 0.4,
    marginTop: '2px',
  },
};
