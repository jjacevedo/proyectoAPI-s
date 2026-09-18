import styles from './JudgeVerdict.module.css';

type Props = {
  verdict: string | null;
  reasoning: string | null;
  error: string | null;
};

const VERDICT_STYLE: Record<string, { label: string; className: string }> = {
  multi: { label: 'Multi-LLM gana', className: styles.pillGreen },
  single: { label: 'Single-LLM gana', className: styles.pillTerracotta },
  tie: { label: 'Empate', className: styles.pillAmber },
};

export function JudgeVerdict({ verdict, reasoning, error }: Props) {
  if (error) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <StarIcon />
          <span className={styles.title}>Veredicto del juez</span>
        </div>
        <p className={styles.errorText}>Juez no disponible: {error}</p>
      </div>
    );
  }

  if (!verdict) return null;

  const style = VERDICT_STYLE[verdict] ?? { label: verdict, className: styles.pillAmber };

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <StarIcon />
        <span className={styles.title}>Veredicto del juez</span>
      </div>
      <div className={styles.pillRow}>
        <span className={`${styles.pill} ${style.className}`}>{style.label}</span>
      </div>
      {reasoning && <p className={styles.reasoning}>{reasoning}</p>}
    </div>
  );
}

function StarIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" strokeWidth="2">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}
