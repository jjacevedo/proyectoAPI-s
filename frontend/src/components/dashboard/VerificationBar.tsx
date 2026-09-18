import styles from './VerificationBar.module.css';

type Props = {
  label: string;
  percent: number | null;
  color: 'green' | 'amber';
};

export function VerificationBar({ label, percent, color }: Props) {
  const width = percent == null ? 0 : Math.round(percent * 100);
  return (
    <div>
      <div className={styles.row}>
        <span className={styles.label}>{label}</span>
        <span className={color === 'green' ? styles.valueGreen : styles.valueAmber}>
          {percent == null ? 'N/D' : `${width}%`}
        </span>
      </div>
      <div className={styles.track}>
        <div
          className={color === 'green' ? styles.fillGreen : styles.fillAmber}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}
