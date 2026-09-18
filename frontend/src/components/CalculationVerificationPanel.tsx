import type { CalculationVerificationResponse } from '@/types/chat';
import styles from './panels.module.css';

type Props = {
  referenceCalculation: string | null;
  verifications: CalculationVerificationResponse[];
};

export function CalculationVerificationPanel({ referenceCalculation, verifications }: Props) {
  if (verifications.length === 0) return null;

  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Verificación de cálculo (valor de referencia independiente, no opinión)</h3>
      {referenceCalculation && (
        <details className={styles.detail}>
          <summary>Script de cálculo generado</summary>
          <pre className={styles.pre}>{referenceCalculation}</pre>
        </details>
      )}
      {verifications.map((verification, index) => (
        <details key={`${verification.provider}-${verification.model}-${index}`} className={styles.detail}>
          <summary>
            {verification.provider} / {verification.model}:{' '}
            {verification.error
              ? 'no verificado'
              : verification.passed
                ? `COINCIDE (${verification.reference_value})`
                : `DIFIERE (dijo ${verification.candidate_value}, referencia ${verification.reference_value})`}
          </summary>
          {verification.error && <p className={styles.error}>{verification.error}</p>}
        </details>
      ))}
    </div>
  );
}
