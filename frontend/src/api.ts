import axios from 'axios';
import type { Job, JobListResponse, BrandKit, BrandColors, BrandFonts, ProgressEvent } from './types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

/* ─── Jobs ─── */

export async function createJob(file: File, options: Record<string, unknown>): Promise<Job> {
  const form = new FormData();
  form.append('file', file);
  form.append('options', JSON.stringify(options));
  const { data } = await api.post<Job>('/jobs', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function listJobs(params?: {
  status?: string;
  mode?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<JobListResponse> {
  const { data } = await api.get<JobListResponse>('/jobs', { params });
  return data;
}

export async function getJob(id: string): Promise<Job> {
  const { data } = await api.get<Job>(`/jobs/${id}`);
  return data;
}

export async function deleteJob(id: string): Promise<void> {
  await api.delete(`/jobs/${id}`);
}

export async function togglePin(id: string): Promise<{ pinned: boolean }> {
  const { data } = await api.patch<{ pinned: boolean }>(`/jobs/${id}/pin`);
  return data;
}

export async function getProgress(id: string): Promise<{
  job_id: string;
  status: string;
  events: ProgressEvent[];
}> {
  const { data } = await api.get(`/jobs/${id}/progress`);
  return data;
}

export function getDownloadUrl(id: string): string {
  return `/api/v1/jobs/${id}/download`;
}

export function getSpecsUrl(id: string): string {
  return `/api/v1/jobs/${id}/specs`;
}

/* ─── Brand Kits ─── */

export async function listBrands(): Promise<BrandKit[]> {
  const { data } = await api.get<BrandKit[]>('/brands');
  return data;
}

export async function getBrand(id: string): Promise<BrandKit> {
  const { data } = await api.get<BrandKit>(`/brands/${id}`);
  return data;
}

export async function createBrand(brand: {
  name: string;
  colors?: BrandColors;
  fonts?: BrandFonts;
  logo_position?: string;
}): Promise<BrandKit> {
  const { data } = await api.post<BrandKit>('/brands', brand);
  return data;
}

export async function updateBrand(
  id: string,
  brand: Partial<{
    name: string;
    colors: BrandColors;
    fonts: BrandFonts;
    logo_position: string;
  }>
): Promise<BrandKit> {
  const { data } = await api.put<BrandKit>(`/brands/${id}`, brand);
  return data;
}

export async function deleteBrand(id: string): Promise<void> {
  await api.delete(`/brands/${id}`);
}

/* ─── WebSocket ─── */

export function connectJobWs(
  jobId: string,
  onEvent: (event: ProgressEvent) => void,
  onClose?: () => void
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = window.location.host;
  const ws = new WebSocket(`${protocol}://${host}/api/v1/ws/jobs/${jobId}`);

  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data) as ProgressEvent;
      onEvent(event);
    } catch {
      // ignore non-JSON messages
    }
  };

  ws.onerror = () => {
    // Error logged by browser; close handler will trigger reconnect
  };

  ws.onclose = () => onClose?.();

  return ws;
}

/* ─── NotebookLM Auth ─── */

export async function nlmAuthStatus(): Promise<{ authenticated: boolean }> {
  const { data } = await api.get<{ authenticated: boolean }>('/auth/notebooklm/status');
  return data;
}

export async function nlmAuthStart(): Promise<{ screenshot: string }> {
  const { data } = await api.post<{ screenshot: string }>('/auth/notebooklm/start');
  return data;
}

export async function nlmAuthScreenshot(): Promise<{ screenshot: string }> {
  const { data } = await api.get<{ screenshot: string }>('/auth/notebooklm/screenshot');
  return data;
}

export async function nlmAuthClick(x: number, y: number): Promise<{ screenshot: string }> {
  const { data } = await api.post<{ screenshot: string }>('/auth/notebooklm/click', { x, y });
  return data;
}

export async function nlmAuthType(text: string): Promise<{ screenshot: string }> {
  const { data } = await api.post<{ screenshot: string }>('/auth/notebooklm/type', { text });
  return data;
}

export async function nlmAuthKey(key: string): Promise<{ screenshot: string }> {
  const { data } = await api.post<{ screenshot: string }>('/auth/notebooklm/key', { key });
  return data;
}

export async function nlmAuthComplete(): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post<{ success: boolean; message: string }>('/auth/notebooklm/complete');
  return data;
}

export async function nlmAuthCancel(): Promise<void> {
  await api.post('/auth/notebooklm/cancel');
}

/* ─── Health ─── */

export async function healthCheck(): Promise<{ status: string }> {
  const { data } = await api.get<{ status: string }>('/health');
  return data;
}
