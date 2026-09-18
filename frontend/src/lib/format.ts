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
