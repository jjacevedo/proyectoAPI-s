import styles from './EvalComparisonBar.module.css';

type Props = {
  multiWins: number;
  singleWins: number;
  ties: number;
  judgeUnavailable: number;
};

const LABEL_MIN_PERCENT = 10;

export function EvalComparisonBar({ multiWins, singleWins, ties, judgeUnavailable }: Props) {
  const total = multiWins + singleWins + ties + judgeUnavailable;

  if (total === 0) {
    return <p className={styles.empty}>Sin comparaciones todavía.</p>;
  }

  const segments = [
    { count: multiWins, className: styles.segMulti, label: `Multi: ${multiWins}` },
    { count: singleWins, className: styles.segSingle, label: `Single: ${singleWins}` },
    { count: ties, className: styles.segTie, label: `${ties}` },
    { count: judgeUnavailable, className: styles.segNone, label: `${judgeUnavailable}` },
  ];

  return (
    <>
      <div className={styles.bar}>
        {segments
          .filter((s) => s.count > 0)
          .map((segment, index) => {
            const percent = (segment.count / total) * 100;
            return (
              <div key={index} className={segment.className} style={{ width: `${percent}%` }}>
                {percent >= LABEL_MIN_PERCENT && segment.label}
              </div>
            );
          })}
      </div>
      <div className={styles.legend}>
        <LegendItem className={styles.dotMulti} label="Multi gana" />
        <LegendItem className={styles.dotSingle} label="Single gana" />
        <LegendItem className={styles.dotTie} label="Empate" />
        <LegendItem className={styles.dotNone} label="Sin veredicto" />
      </div>
    </>
  );
}

function LegendItem({ className, label }: { className: string; label: string }) {
  return (
    <div className={styles.legendItem}>
      <span className={`${styles.legendDot} ${className}`} />
      {label}
    </div>
  );
}
