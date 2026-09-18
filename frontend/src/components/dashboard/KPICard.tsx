import styles from './KPICard.module.css';

type Props = {
  label: string;
  value: string;
  sublabel?: string;
};

export function KPICard({ label, value, sublabel }: Props) {
  return (
    <div className={styles.card}>
      <div className={styles.label}>{label}</div>
      <div className={styles.value}>{value}</div>
      {sublabel && <div className={styles.sublabel}>{sublabel}</div>}
    </div>
  );
}
