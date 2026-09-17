import type { CalculationVerificationResponse } from '@/types/chat';

type Props = {
  referenceCalculation: string | null;
  verifications: CalculationVerificationResponse[];
};

export function CalculationVerificationPanel({ referenceCalculation, verifications }: Props) {
  if (verifications.length === 0) return null;

  return (
    <section className="card">
      <h2>Verificación de cálculo (valor de referencia independiente, no opinión)</h2>
      {referenceCalculation && (
        <details>
          <summary>Script de cálculo generado</summary>
          <pre className="response">{referenceCalculation}</pre>
        </details>
      )}
      {verifications.map((verification, index) => (
        <details key={`${verification.provider}-${verification.model}-${index}`}>
          <summary>
            {verification.provider} / {verification.model}:{' '}
            {verification.error
              ? 'no verificado'
              : verification.passed
                ? `COINCIDE (${verification.reference_value})`
                : `DIFIERE (dijo ${verification.candidate_value}, referencia ${verification.reference_value})`}
          </summary>
          {verification.error && <p className="error">{verification.error}</p>}
        </details>
      ))}
    </section>
  );
}
