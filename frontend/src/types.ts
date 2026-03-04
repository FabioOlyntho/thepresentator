/* ─── API Types matching backend schemas ─── */

export interface JobSlide {
  slide_number: number;
  slide_type: string | null;
  title: string | null;
  thumbnail_url: string | null;
}

export interface Job {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  mode: 'editable' | 'full_slide' | 'notebooklm' | 'ocr_editable' | 'translate';
  title: string | null;
  language: string | null;
  target_language: string | null;
  slide_count: number;
  prompt: string | null;
  brand_kit_id: string | null;
  input_filename: string;
  time_total: number | null;
  error_message: string | null;
  pinned: boolean;
  created_at: string;
  updated_at: string;
  slides: JobSlide[];
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
}

export interface JobOptions {
  mode: string;
  title?: string;
  language?: string;
  target_language?: string;
  slide_count?: number;
  prompt?: string;
  model?: string;
  brand_kit_id?: string;
}

export interface BrandColors {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text_dark: string;
  text_light: string;
  highlight: string;
}

export interface BrandFonts {
  title: string;
  body: string;
  accent: string;
}

export interface BrandKit {
  id: string;
  name: string;
  logo_path: string | null;
  colors: BrandColors;
  fonts: BrandFonts;
  logo_position: string;
  is_default: boolean;
  created_at: string;
}

export interface ProgressEvent {
  step: string;
  progress: number;
  message: string;
}

/* ─── UI Types ─── */

export type GenerationMode = 'editable' | 'full_slide' | 'notebooklm' | 'ocr_editable' | 'translate';

export interface ModeOption {
  id: GenerationMode;
  label: string;
  description: string;
  recommended?: boolean;
}

export const MODE_OPTIONS: ModeOption[] = [
  {
    id: 'ocr_editable',
    label: 'OCR + Editable',
    description: 'Best quality NotebookLM slides, converted to editable format',
    recommended: true,
  },
  {
    id: 'editable',
    label: 'Editable',
    description: 'Fast, AI-generated editable slides with Recodme layouts',
  },
  {
    id: 'notebooklm',
    label: 'NotebookLM',
    description: 'Highest visual quality, image-based (non-editable)',
  },
  {
    id: 'full_slide',
    label: 'Full Slide',
    description: 'Single AI-generated image per slide',
  },
];

export const LANGUAGES = [
  { code: 'auto', label: 'Auto-detect' },
  { code: 'ES', label: 'Spanish' },
  { code: 'EN', label: 'English' },
  { code: 'PT', label: 'Portuguese' },
  { code: 'FR', label: 'French' },
  { code: 'DE', label: 'German' },
  { code: 'IT', label: 'Italian' },
];

export const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
};

export const STATUS_COLORS: Record<string, string> = {
  pending: 'var(--pr-warning)',
  processing: 'var(--pr-teal)',
  completed: 'var(--pr-success)',
  failed: 'var(--pr-error)',
};
