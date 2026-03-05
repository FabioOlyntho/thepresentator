import { type CSSProperties } from 'react';
import type { ProgressEvent } from '../types';

const STEPS = [
  { key: 'uploading', label: 'Upload' },
  { key: 'extracting', label: 'Extract' },
  { key: 'generating', label: 'Generate' },
  { key: 'building', label: 'Build' },
  { key: 'completed', label: 'Done' },
];

interface Props {
  events: ProgressEvent[];
  status: string;
}

export default function ProgressTracker({ events, status }: Props) {
  const lastEvent = events.length > 0 ? events[events.length - 1] : null;
  const currentStep = lastEvent?.step ?? 'uploading';
  const progress = lastEvent?.progress ?? 0;

  const currentIdx = STEPS.findIndex((s) => s.key === currentStep);
  const activeIdx = currentIdx >= 0 ? currentIdx : 0;
  const isFailed = status === 'failed';
  const isComplete = status === 'completed' || currentStep === 'completed';

  return (
    <div style={styles.container}>
      {/* Step circles with connecting lines */}
      <div style={styles.steps}>
        {STEPS.map((step, i) => {
          const isDone = i < activeIdx || isComplete;
          const isActive = i === activeIdx && !isComplete && !isFailed;

          return (
            <div key={step.key} style={styles.stepGroup}>
              {i > 0 && (
                <div style={{
                  ...styles.line,
                  background: isDone ? 'var(--pr-teal)' : 'var(--pr-beige)',
                }} />
              )}
              <div style={{
                ...styles.circle,
                ...(isDone ? styles.circleDone : {}),
                ...(isActive ? styles.circleActive : {}),
                ...(isFailed && isActive ? styles.circleFailed : {}),
              }}>
                {isDone ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <span style={styles.circleNum}>{i + 1}</span>
                )}
              </div>
              <div style={{
                ...styles.stepLabel,
                ...(isDone || isActive ? styles.stepLabelActive : {}),
              }}>
                {step.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      {!isComplete && (
        <div style={styles.barOuter}>
          <div style={{
            ...styles.barInner,
            width: `${progress}%`,
            ...(isFailed ? { background: 'var(--pr-error)' } : {}),
          }} />
        </div>
      )}

      {/* Status message */}
      {lastEvent && (
        <div style={{
          ...styles.message,
          ...(isFailed ? { color: 'var(--pr-error)' } : {}),
        }}>
          {lastEvent.message}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  container: {
    animation: 'fadeInUp 0.3s ease',
  },
  steps: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    gap: '0',
    marginBottom: '24px',
  },
  stepGroup: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    position: 'relative',
    flex: 1,
  },
  line: {
    position: 'absolute',
    top: '16px',
    right: '50%',
    width: '100%',
    height: '2px',
    transition: 'background 0.3s ease',
  },
  circle: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    border: '2px solid var(--pr-beige)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--pr-cream)',
    position: 'relative',
    zIndex: 1,
    transition: 'all 0.3s ease',
  },
  circleDone: {
    background: 'var(--pr-teal)',
    borderColor: 'var(--pr-teal)',
  },
  circleActive: {
    borderColor: 'var(--pr-red)',
    boxShadow: '0 0 0 4px var(--pr-red-glow)',
    animation: 'pulse 2s ease-in-out infinite',
  },
  circleFailed: {
    borderColor: 'var(--pr-error)',
    boxShadow: '0 0 0 4px rgba(220, 38, 38, 0.15)',
    animation: 'none',
  },
  circleNum: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--pr-gray)',
  },
  stepLabel: {
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--pr-gray)',
    marginTop: '6px',
    textAlign: 'center',
  },
  stepLabelActive: {
    color: 'var(--pr-charcoal)',
  },
  barOuter: {
    height: '6px',
    borderRadius: '3px',
    background: 'var(--pr-cream-warm)',
    overflow: 'hidden',
    marginBottom: '12px',
  },
  barInner: {
    height: '100%',
    borderRadius: '3px',
    background: 'linear-gradient(90deg, var(--pr-teal), var(--pr-teal-light))',
    transition: 'width 0.5s ease',
    animation: 'progressFill 0.5s ease',
  },
  message: {
    fontSize: '13px',
    color: 'var(--pr-gray)',
    textAlign: 'center',
  },
};
