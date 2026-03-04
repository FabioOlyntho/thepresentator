import { useState, type CSSProperties } from 'react';
import type { JobSlide } from '../types';

interface Props {
  slides: JobSlide[];
  jobId: string;
}

export default function SlideCarousel({ slides, jobId }: Props) {
  const [lightbox, setLightbox] = useState<number | null>(null);

  if (slides.length === 0) {
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--pr-beige)" strokeWidth="1.5">
            <rect x="2" y="3" width="20" height="14" rx="2" />
            <line x1="8" y1="21" x2="16" y2="21" />
            <line x1="12" y1="17" x2="12" y2="21" />
          </svg>
        </div>
        <div style={styles.emptyText}>No slide previews available</div>
      </div>
    );
  }

  return (
    <>
      <div style={styles.grid}>
        {slides.map((slide, i) => (
          <button
            key={slide.slide_number}
            onClick={() => setLightbox(i)}
            style={styles.thumb}
            className={`stagger-${Math.min(i + 1, 6)}`}
          >
            {slide.thumbnail_url ? (
              <img
                src={`/api/v1/jobs/${jobId}/thumbnails/${slide.slide_number}`}
                alt={`Slide ${slide.slide_number}`}
                style={styles.thumbImg}
              />
            ) : (
              <div style={styles.thumbPlaceholder}>
                <div style={styles.thumbType}>{slide.slide_type ?? 'content'}</div>
                <div style={styles.thumbTitle}>{slide.title ?? `Slide ${slide.slide_number}`}</div>
              </div>
            )}
            <div style={styles.thumbNumber}>{slide.slide_number}</div>
          </button>
        ))}
      </div>

      {/* Lightbox */}
      {lightbox !== null && (
        <div style={styles.lightbox} onClick={() => setLightbox(null)}>
          <div style={styles.lightboxContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.lightboxHeader}>
              <span style={styles.lightboxTitle}>
                Slide {slides[lightbox].slide_number} — {slides[lightbox].title ?? slides[lightbox].slide_type ?? 'Content'}
              </span>
              <button onClick={() => setLightbox(null)} style={styles.lightboxClose}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div style={styles.lightboxBody}>
              {slides[lightbox].thumbnail_url ? (
                <img
                  src={`/api/v1/jobs/${jobId}/thumbnails/${slides[lightbox].slide_number}`}
                  alt={`Slide ${slides[lightbox].slide_number}`}
                  style={styles.lightboxImg}
                />
              ) : (
                <div style={styles.lightboxPlaceholder}>
                  <div style={{ fontSize: '18px', fontWeight: 600 }}>{slides[lightbox].slide_type}</div>
                  <div style={{ fontSize: '14px', marginTop: '8px', color: 'var(--pr-gray)' }}>
                    {slides[lightbox].title ?? 'No preview available'}
                  </div>
                </div>
              )}
            </div>
            <div style={styles.lightboxNav}>
              <button
                disabled={lightbox === 0}
                onClick={() => setLightbox(lightbox - 1)}
                style={{
                  ...styles.lightboxBtn,
                  opacity: lightbox === 0 ? 0.3 : 1,
                }}
              >
                Previous
              </button>
              <span style={styles.lightboxCounter}>
                {lightbox + 1} / {slides.length}
              </span>
              <button
                disabled={lightbox === slides.length - 1}
                onClick={() => setLightbox(lightbox + 1)}
                style={{
                  ...styles.lightboxBtn,
                  opacity: lightbox === slides.length - 1 ? 0.3 : 1,
                }}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const styles: Record<string, CSSProperties> = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
    gap: '14px',
  },
  thumb: {
    position: 'relative',
    aspectRatio: '16/10',
    borderRadius: 'var(--radius-md)',
    border: '1.5px solid var(--pr-beige)',
    overflow: 'hidden',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    background: 'var(--pr-white)',
    padding: 0,
    animation: 'fadeInUp 0.3s ease both',
  },
  thumbImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  thumbPlaceholder: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '8px',
    background: 'linear-gradient(135deg, var(--pr-teal) 0%, var(--pr-teal-light) 100%)',
  },
  thumbType: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    fontWeight: 500,
    color: 'var(--pr-beige)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  thumbTitle: {
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--pr-white)',
    textAlign: 'center',
    marginTop: '4px',
    lineHeight: 1.3,
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  thumbNumber: {
    position: 'absolute',
    bottom: '4px',
    right: '6px',
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    fontWeight: 500,
    color: 'var(--pr-white)',
    background: 'rgba(1, 38, 45, 0.7)',
    padding: '1px 5px',
    borderRadius: '3px',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    padding: '40px 0',
  },
  emptyIcon: {
    opacity: 0.5,
  },
  emptyText: {
    fontSize: '13px',
    color: 'var(--pr-gray)',
  },
  lightbox: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(1, 38, 45, 0.85)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    animation: 'fadeIn 0.2s ease',
  },
  lightboxContent: {
    background: 'var(--pr-white)',
    borderRadius: 'var(--radius-lg)',
    maxWidth: '800px',
    width: '90%',
    maxHeight: '90vh',
    overflow: 'hidden',
    animation: 'scaleIn 0.2s ease',
  },
  lightboxHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid var(--pr-beige)',
  },
  lightboxTitle: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--pr-charcoal)',
  },
  lightboxClose: {
    color: 'var(--pr-gray)',
    padding: '4px',
    cursor: 'pointer',
  },
  lightboxBody: {
    padding: '20px',
    display: 'flex',
    justifyContent: 'center',
  },
  lightboxImg: {
    maxWidth: '100%',
    maxHeight: '60vh',
    borderRadius: 'var(--radius-sm)',
  },
  lightboxPlaceholder: {
    width: '100%',
    aspectRatio: '16/10',
    background: 'linear-gradient(135deg, var(--pr-teal) 0%, var(--pr-teal-light) 100%)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--pr-white)',
    maxHeight: '400px',
  },
  lightboxNav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 20px',
    borderTop: '1px solid var(--pr-beige)',
  },
  lightboxBtn: {
    padding: '6px 16px',
    borderRadius: 'var(--radius-sm)',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--pr-teal)',
    background: 'var(--pr-cream)',
    cursor: 'pointer',
    transition: 'opacity 0.15s',
  },
  lightboxCounter: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--pr-gray)',
  },
};
