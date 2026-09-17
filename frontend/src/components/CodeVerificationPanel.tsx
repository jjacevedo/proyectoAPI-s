import type { CodeVerificationResponse } from '@/types/chat';

type Props = {
  generatedTests: string | null;
  verifications: CodeVerificationResponse[];
};

export function CodeVerificationPanel({ generatedTests, verifications }: Props) {
  if (verifications.length === 0) return null;

  return (
    <section className="card">
      <h2>Verificación de código (ejecución real, no opinión)</h2>
      {generatedTests && (
        <details>
          <summary>Tests generados</summary>
          <pre className="response">{generatedTests}</pre>
        </details>
      )}
      {verifications.map((verification, index) => (
        <details key={`${verification.provider}-${verification.model}-${index}`}>
          <summary>
            {verification.provider} / {verification.model}:{' '}
            {verification.error
              ? 'no verificado'
              : verification.passed
                ? `PASSED ${verification.tests_passed}/${verification.tests_run}`
                : `FAILED ${verification.tests_failed}/${verification.tests_run}`}
          </summary>
          {verification.error && <p className="error">{verification.error}</p>}
          {verification.stdout && (
            <div>
              <strong>stdout</strong>
              <pre className="response">{verification.stdout}</pre>
            </div>
          )}
          {verification.stderr && (
            <div>
              <strong>stderr</strong>
              <pre className="response">{verification.stderr}</pre>
            </div>
          )}
        </details>
      ))}
    </section>
  );
}
