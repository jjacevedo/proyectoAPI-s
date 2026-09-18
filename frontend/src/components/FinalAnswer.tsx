import styles from './FinalAnswer.module.css';

export function FinalAnswer({ answer }: { answer: string }) {
  return <div className={styles.answer}>{answer}</div>;
}
