import { useState, useRef, useEffect, useCallback, type CSSProperties } from 'react';
import {
  nlmAuthStart,
  nlmAuthClick,
  nlmAuthType,
  nlmAuthKey,
  nlmAuthComplete,
  nlmAuthCancel,
} from '../api';

interface Props {
  onSuccess: () => void;
  onCancel: () => void;
}

const VIEWPORT_W = 1024;
const VIEWPORT_H = 700;

/** Keys that should be forwarded to the remote browser as-is */
const FORWARD_KEYS = new Set([
  'Enter', 'Tab', 'Backspace', 'Delete', 'Escape',
  'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
  'Home', 'End',
]);

export default function NlmAuthModal({ onSuccess, onCancel }: Props) {
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'active' | 'saving' | 'error'>('idle');
  const [error, setError] = useState('');
  const imgRef = useRef<HTMLImageElement>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const charBuffer = useRef('');
  const flushTimer = useRef<number | null>(null);
  const busyRef = useRef(false);

  // Focus the browser frame when active
  useEffect(() => {
    if (status === 'active' && frameRef.current) {
      frameRef.current.focus();
    }
  }, [status, screenshot]);

  async function handleStart() {
    setStatus('loading');
    setError('');
    try {
      const res = await nlmAuthStart();
      setScreenshot(res.screenshot);
      setStatus('active');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start browser');
      setStatus('error');
    }
  }

  async function handleClick(e: React.MouseEvent<HTMLImageElement>) {
    if (status !== 'active' || !imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const scaleX = VIEWPORT_W / rect.width;
    const scaleY = VIEWPORT_H / rect.height;
    const x = Math.round((e.clientX - rect.left) * scaleX);
    const y = Math.round((e.clientY - rect.top) * scaleY);

    setLoading(true);
    try {
      const res = await nlmAuthClick(x, y);
      setScreenshot(res.screenshot);
    } catch {
      // ignore click errors
    }
    setLoading(false);
    // Re-focus the frame so keyboard input keeps working
    frameRef.current?.focus();
  }

  /** Flush any buffered characters to the remote browser */
  const flushBuffer = useCallback(async () => {
    if (flushTimer.current) {
      clearTimeout(flushTimer.current);
      flushTimer.current = null;
    }
    const text = charBuffer.current;
    if (!text) return;
    charBuffer.current = '';

    if (busyRef.current) return;
    busyRef.current = true;
    setLoading(true);
    try {
      const res = await nlmAuthType(text);
      setScreenshot(res.screenshot);
    } catch {
      // ignore
    }
    setLoading(false);
    busyRef.current = false;
  }, []);

  /** Send a special key to the remote browser */
  const sendKey = useCallback(async (key: string) => {
    // Flush any pending characters first
    await flushBuffer();

    if (busyRef.current) return;
    busyRef.current = true;
    setLoading(true);
    try {
      const res = await nlmAuthKey(key);
      setScreenshot(res.screenshot);
    } catch {
      // ignore
    }
    setLoading(false);
    busyRef.current = false;
  }, [flushBuffer]);

  /** Handle keyboard events on the browser frame */
  function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (status !== 'active' || loading) return;

    // Don't interfere with browser shortcuts
    if (e.ctrlKey || e.metaKey) {
      // Allow Ctrl+V (paste) — handled by onPaste
      if (e.key === 'v' || e.key === 'V') return;
      // Allow Ctrl+A (select all in remote browser)
      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        sendKey('Control+a');
        return;
      }
      return;
    }

    e.preventDefault();
    e.stopPropagation();

    // Special keys: send immediately
    if (FORWARD_KEYS.has(e.key)) {
      sendKey(e.key);
      return;
    }

    // Printable character: buffer it
    if (e.key.length === 1) {
      charBuffer.current += e.key;
      // Debounce: flush after 250ms of no typing
      if (flushTimer.current) clearTimeout(flushTimer.current);
      flushTimer.current = window.setTimeout(() => {
        flushBuffer();
      }, 250);
    }
  }

  /** Handle paste events */
  async function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault();
    const text = e.clipboardData.getData('text');
    if (!text) return;

    charBuffer.current += text;
    flushBuffer();
  }

  async function handleComplete() {
    setStatus('saving');
    try {
      const res = await nlmAuthComplete();
      if (res.success) {
        onSuccess();
      } else {
        setError(res.message);
        setStatus('active');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save');
      setStatus('active');
    }
  }

  async function handleCancel() {
    await nlmAuthCancel().catch(() => {});
    onCancel();
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <div style={styles.header}>
          <h2 style={styles.title}>NotebookLM Authentication</h2>
          <button onClick={handleCancel} style={styles.closeBtn}>&times;</button>
        </div>

        {status === 'idle' && (
          <div style={styles.startSection}>
            <p style={styles.desc}>
              NotebookLM requires Google sign-in. Click below to open a secure
              browser session — sign in with your Google account, then click
              "Save & Continue".
            </p>
            <button onClick={handleStart} style={styles.startBtn}>
              Open Google Sign-In
            </button>
          </div>
        )}

        {status === 'loading' && (
          <div style={styles.startSection}>
            <p style={styles.desc}>Starting browser...</p>
            <div style={styles.spinner} />
          </div>
        )}

        {status === 'error' && (
          <div style={styles.startSection}>
            <p style={{ ...styles.desc, color: 'var(--pr-error)' }}>{error}</p>
            <button onClick={handleStart} style={styles.startBtn}>
              Try Again
            </button>
          </div>
        )}

        {(status === 'active' || status === 'saving') && screenshot && (
          <>
            <div
              ref={frameRef}
              tabIndex={0}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              style={styles.browserFrame}
            >
              <img
                ref={imgRef}
                src={`data:image/png;base64,${screenshot}`}
                alt="Browser"
                draggable={false}
                style={{
                  ...styles.browserImg,
                  opacity: loading ? 0.7 : 1,
                  cursor: loading ? 'wait' : 'pointer',
                }}
                onClick={handleClick}
              />
              {loading && <div style={styles.imgSpinner} />}
            </div>

            <p style={styles.hint}>
              Click on a field above, then type — your keyboard goes directly into the browser.
              You can also paste (Ctrl+V).
            </p>

            {error && <p style={styles.errorMsg}>{error}</p>}

            <div style={styles.actions}>
              <button onClick={handleCancel} style={styles.cancelBtn} disabled={status === 'saving'}>
                Cancel
              </button>
              <button onClick={handleComplete} style={styles.completeBtn} disabled={status === 'saving'}>
                {status === 'saving' ? 'Saving...' : 'Save & Continue'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
    backdropFilter: 'blur(4px)',
  },
  modal: {
    background: 'var(--pr-white)',
    borderRadius: '16px',
    width: '90vw',
    maxWidth: '1100px',
    maxHeight: '90vh',
    overflow: 'auto',
    boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    borderBottom: '1px solid var(--pr-beige)',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: '18px',
    color: 'var(--pr-charcoal)',
    margin: 0,
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    color: 'var(--pr-gray)',
    cursor: 'pointer',
    padding: '4px 8px',
    lineHeight: 1,
  },
  startSection: {
    padding: '40px 24px',
    textAlign: 'center',
  },
  desc: {
    fontSize: '14px',
    color: 'var(--pr-gray)',
    lineHeight: 1.6,
    maxWidth: '500px',
    margin: '0 auto 24px',
  },
  startBtn: {
    padding: '12px 32px',
    borderRadius: '8px',
    background: 'var(--pr-red)',
    color: 'var(--pr-white)',
    fontSize: '15px',
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--pr-beige)',
    borderTop: '3px solid var(--pr-red)',
    borderRadius: '50%',
    margin: '0 auto',
    animation: 'spin 0.8s linear infinite',
  },
  browserFrame: {
    position: 'relative',
    margin: '0 16px',
    borderRadius: '8px',
    overflow: 'hidden',
    border: '2px solid var(--pr-teal)',
    background: '#f5f5f5',
    outline: 'none',
  },
  browserImg: {
    width: '100%',
    height: 'auto',
    display: 'block',
    transition: 'opacity 0.2s',
    userSelect: 'none',
  },
  imgSpinner: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '40px',
    height: '40px',
    border: '3px solid rgba(255,255,255,0.4)',
    borderTop: '3px solid var(--pr-red)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  hint: {
    fontSize: '12px',
    color: 'var(--pr-gray)',
    textAlign: 'center',
    margin: '8px 16px 0',
    opacity: 0.7,
  },
  errorMsg: {
    fontSize: '13px',
    color: 'var(--pr-error)',
    padding: '0 16px',
    margin: '8px 0 0',
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '16px 24px',
    borderTop: '1px solid var(--pr-beige)',
    marginTop: '12px',
  },
  cancelBtn: {
    padding: '10px 20px',
    borderRadius: '8px',
    background: 'transparent',
    color: 'var(--pr-gray)',
    fontSize: '14px',
    border: '1px solid var(--pr-beige)',
    cursor: 'pointer',
  },
  completeBtn: {
    padding: '10px 24px',
    borderRadius: '8px',
    background: 'var(--pr-red)',
    color: 'var(--pr-white)',
    fontSize: '14px',
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
  },
};
