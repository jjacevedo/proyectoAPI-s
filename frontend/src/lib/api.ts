import type { ChatResponse, ConversationMode } from '@/types/chat';
import type { ConversationListResponse, MessageListResponse } from '@/types/conversation';
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

  if (response.status === 204) return undefined as T;
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

async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { method: 'DELETE' });
  return handleResponse<T>(response);
}

export async function sendChat(
  prompt: string,
  options?: { conversationId?: number | null; mode?: ConversationMode }
): Promise<ChatResponse> {
  return postJson<ChatResponse>('/api/chat', {
    prompt,
    conversation_id: options?.conversationId ?? null,
    mode: options?.mode ?? null,
  });
}

export async function sendEvaluate(prompt: string): Promise<EvaluateResponse> {
  return postJson<EvaluateResponse>('/api/evaluate', { prompt });
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return getJson<DashboardStats>('/api/dashboard/stats');
}

export async function listConversations(): Promise<ConversationListResponse> {
  return getJson<ConversationListResponse>('/api/conversations');
}

export async function getConversationMessages(id: number): Promise<MessageListResponse> {
  return getJson<MessageListResponse>(`/api/conversations/${id}/messages`);
}

export async function deleteConversation(id: number): Promise<void> {
  return deleteJson<void>(`/api/conversations/${id}`);
}
