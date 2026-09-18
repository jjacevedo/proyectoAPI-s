import type { CodeVerificationResponse } from '@/types/chat';
import styles from './panels.module.css';

type Props = {
  generatedTests: string | null;
  verifications: CodeVerificationResponse[];
};

export function CodeVerificationPanel({ generatedTests, verifications }: Props) {
  if (verifications.length === 0) return null;

  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Verificación de código (ejecución real, no opinión)</h3>
      {generatedTests && (
        <details className={styles.detail}>
          <summary>Tests generados</summary>
          <pre className={styles.pre}>{generatedTests}</pre>
        </details>
      )}
      {verifications.map((verification, index) => (
        <details key={`${verification.provider}-${verification.model}-${index}`} className={styles.detail}>
          <summary>
            {verification.provider} / {verification.model}:{' '}
            {verification.error
              ? 'no verificado'
              : verification.passed
                ? `PASSED ${verification.tests_passed}/${verification.tests_run}`
                : `FAILED ${verification.tests_failed}/${verification.tests_run}`}
          </summary>
          {verification.error && <p className={styles.error}>{verification.error}</p>}
          {verification.stdout && (
            <div>
              <strong>stdout</strong>
              <pre className={styles.pre}>{verification.stdout}</pre>
            </div>
          )}
          {verification.stderr && (
            <div>
              <strong>stderr</strong>
              <pre className={styles.pre}>{verification.stderr}</pre>
            </div>
          )}
        </details>
      ))}
    </div>
  );
}
