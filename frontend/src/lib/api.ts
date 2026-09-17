import type { ChatResponse } from '@/types/chat';
import type { DashboardStats } from '@/types/dashboard';
import type { EvaluateResponse } from '@/types/evaluate';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = data.detail ?? message;
    } catch {
      // Keep the generic HTTP error.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(response);
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  return handleResponse<T>(response);
}

export async function sendChat(prompt: string): Promise<ChatResponse> {
  return postJson<ChatResponse>('/api/chat', { prompt });
}

export async function sendEvaluate(prompt: string): Promise<EvaluateResponse> {
  return postJson<EvaluateResponse>('/api/evaluate', { prompt });
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return getJson<DashboardStats>('/api/dashboard/stats');
}
