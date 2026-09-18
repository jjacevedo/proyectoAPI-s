import type { ProviderResponse } from '@/types/chat';
import { formatCost } from '@/lib/format';
import styles from './ModelsParticipated.module.css';

type Props = {
  responses: ProviderResponse[];
  latencyMs?: number;
  costUsd?: number | null;
};

export function ModelsParticipated({ responses, latencyMs, costUsd }: Props) {
  const ok = responses.filter((r) => !r.error);
  const failed = responses.filter((r) => r.error);

  const parts: string[] = [];
  if (ok.length > 0) parts.push(`Sintetizado de ${ok.map((r) => r.provider).join(', ')}`);
  if (latencyMs != null) parts.push(`${(latencyMs / 1000).toFixed(1)}s`);
  if (costUsd !== undefined) parts.push(formatCost(costUsd));

  return (
    <div className={styles.line}>
      {parts.join(' · ')}
      {failed.length > 0 && (
        <span className={styles.failed}> · {failed.map((r) => r.provider).join(', ')} sin respuesta</span>
      )}
    </div>
  );
}
