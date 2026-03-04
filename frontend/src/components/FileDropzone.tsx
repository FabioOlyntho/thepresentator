import { useState, useRef, type CSSProperties, type DragEvent } from 'react';

const ACCEPTED = ['.pdf', '.docx', '.doc', '.txt', '.md', '.pptx'];

interface Props {
  onFile: (file: File) => void;
  file: File | null;
}

export default function FileDropzone({ onFile, file }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrag(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
  }

  function handleDragIn(e: DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function handleDragOut(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) onFile(f);
  }

  function handleClick() {
    inputRef.current?.click();
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) onFile(f);
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div
      style={{
        ...styles.zone,
        ...(dragging ? styles.zoneDragging : {}),
        ...(file ? styles.zoneHasFile : {}),
      }}
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(',')}
        onChange={handleChange}
        style={{ display: 'none' }}
      />

      {file ? (
        <div style={styles.fileInfo}>
          <div style={styles.fileIcon}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--pr-teal)" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <div>
            <div style={styles.fileName}>{file.name}</div>
            <div style={styles.fileMeta}>{formatSize(file.size)}</div>
          </div>
          <div style={styles.changeHint}>Click to change</div>
        </div>
      ) : (
        <>
          <div style={styles.uploadIcon}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={dragging ? 'var(--pr-red)' : 'var(--pr-teal)'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div style={styles.dropText}>
            Drop your document here
          </div>
          <div style={styles.dropHint}>or click to browse</div>
          <div style={styles.formats}>
            {ACCEPTED.map((ext) => (
              <span key={ext} style={styles.badge}>{ext.replace('.', '').toUpperCase()}</span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  zone: {
    border: '2px dashed var(--pr-beige)',
    borderRadius: 'var(--radius-lg)',
    padding: '40px 24px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    background: 'var(--pr-cream-warm)',
    minHeight: '220px',
  },
  zoneDragging: {
    borderColor: 'var(--pr-red)',
    background: 'var(--pr-red-glow)',
    transform: 'scale(1.01)',
  },
  zoneHasFile: {
    borderColor: 'var(--pr-teal)',
    borderStyle: 'solid',
    padding: '24px',
    minHeight: 'auto',
  },
  uploadIcon: {
    opacity: 0.7,
  },
  dropText: {
    fontSize: '16px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
  },
  dropHint: {
    fontSize: '13px',
    color: 'var(--pr-gray)',
  },
  formats: {
    display: 'flex',
    gap: '6px',
    marginTop: '8px',
  },
  badge: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    fontWeight: 500,
    padding: '3px 8px',
    borderRadius: '4px',
    background: 'var(--pr-cream)',
    color: 'var(--pr-teal)',
    border: '1px solid var(--pr-beige)',
  },
  fileInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    width: '100%',
  },
  fileIcon: {
    flexShrink: 0,
  },
  fileName: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
  },
  fileMeta: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--pr-gray)',
    marginTop: '2px',
  },
  changeHint: {
    marginLeft: 'auto',
    fontSize: '12px',
    color: 'var(--pr-gray)',
    fontStyle: 'italic',
  },
};
