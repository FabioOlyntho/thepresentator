import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import type { CSSProperties } from 'react';

export default function Layout() {
  return (
    <div style={styles.shell}>
      <Sidebar />
      <main style={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  shell: {
    display: 'flex',
    minHeight: '100vh',
  },
  content: {
    marginLeft: 'var(--sidebar-width)',
    flex: 1,
    padding: '32px 40px',
    position: 'relative',
    zIndex: 1,
    animation: 'fadeIn 0.3s ease',
  },
};
