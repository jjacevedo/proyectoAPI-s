// Historial de conversaciones para el sidebar. El backend no expone (ni se le pidió agregar) un
// endpoint para listar conversaciones pasadas, así que esta lista vive solo en localStorage del
// navegador: guarda {id, title, updatedAt} por conversación, nunca los mensajes en sí. Por eso
// "cargar" una conversación pasada desde el sidebar puede reanudarla (el próximo envío reusa su
// conversation_id) pero no puede repintar los turnos de esa sesión anterior, que nunca se
// persistieron fuera de la memoria del navegador que los generó.

export type ConversationSummary = {
  id: number;
  title: string;
  updatedAt: string; // ISO 8601
};

const STORAGE_KEY = 'jjapis:conversations';

function readAll(): ConversationSummary[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(conversations: ConversationSummary[]): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch {
    // localStorage puede fallar (modo privado, cuota llena); el historial simplemente no persiste.
  }
}

export function listConversations(): ConversationSummary[] {
  return readAll().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function upsertConversation(id: number, title: string, updatedAt: string): void {
  const all = readAll();
  const existing = all.find((c) => c.id === id);
  if (existing) {
    existing.updatedAt = updatedAt;
  } else {
    all.push({ id, title, updatedAt });
  }
  writeAll(all);
}

export function deriveTitle(prompt: string, maxLength = 40): string {
  const trimmed = prompt.trim();
  return trimmed.length > maxLength ? `${trimmed.slice(0, maxLength).trimEnd()}…` : trimmed;
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return 'Ahora';
  if (diffMin < 60) return `Hace ${diffMin} minuto${diffMin === 1 ? '' : 's'}`;

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `Hace ${diffHours} hora${diffHours === 1 ? '' : 's'}`;

  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDiff = Math.round((startOfToday.getTime() - startOfDate.getTime()) / 86_400_000);
  if (dayDiff === 1) return 'Ayer';

  return date.toLocaleDateString('es', { day: '2-digit', month: 'short' });
}
