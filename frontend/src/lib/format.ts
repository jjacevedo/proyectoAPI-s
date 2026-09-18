export function formatCost(value: number | null): string {
  return value == null ? 'N/D' : `$${value.toFixed(6)}`;
}

export function formatCostShort(value: number | null): string {
  return value == null ? 'N/D' : `$${value.toFixed(4)}`;
}

export function formatPercent(value: number | null): string {
  return value == null ? 'N/D' : `${(value * 100).toFixed(0)}%`;
}

export function formatTokens(value: number): string {
  return value.toLocaleString('es');
}

export function formatLatency(value: number | null): string {
  return value == null ? 'N/D' : `${value.toFixed(0)}ms`;
}

export function formatDelta(value: number, unit: string): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(unit === 'USD' ? 6 : 0)} ${unit}`;
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
