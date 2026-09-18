'use client';

import { useState } from 'react';
import type { ChatResponse } from '@/types/chat';
import { CalculationVerificationPanel } from '@/components/CalculationVerificationPanel';
import { CodeVerificationPanel } from '@/components/CodeVerificationPanel';
import { CritiquesAccordion } from '@/components/CritiquesAccordion';
import { DisagreementNotice } from '@/components/DisagreementNotice';
import { FactSearchPanel } from '@/components/FactSearchPanel';
import { IndividualResponsesAccordion } from '@/components/IndividualResponsesAccordion';
import { RevisionsAccordion } from '@/components/RevisionsAccordion';
import styles from './ExpandableSections.module.css';

type SectionId = 'individual' | 'critique' | 'revisions' | 'verification';

type Props = { response: ChatResponse };

export function ExpandableSections({ response }: Props) {
  const [open, setOpen] = useState<Set<SectionId>>(new Set());

  const hasVerification =
    response.code_verifications.length > 0 ||
    response.calculation_verifications.length > 0 ||
    response.fact_search_results.length > 0 ||
    response.disagreement_level !== 'not_applicable';

  const sections: { id: SectionId; label: string; visible: boolean }[] = [
    { id: 'individual', label: 'Respuestas individuales', visible: response.responses.length > 0 },
    { id: 'critique', label: 'Crítica cruzada', visible: response.critiques.length > 0 },
    { id: 'revisions', label: 'Revisiones', visible: response.revisions.length > 0 },
    { id: 'verification', label: 'Verificación', visible: hasVerification },
  ];

  const visibleSections = sections.filter((s) => s.visible);
  if (visibleSections.length === 0) return null;

  function toggle(id: SectionId) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.pillRow}>
        {visibleSections.map((section) => (
          <button
            key={section.id}
            type="button"
            className={`${styles.pill} ${open.has(section.id) ? styles.pillActive : ''}`}
            onClick={() => toggle(section.id)}
          >
            {section.label}
          </button>
        ))}
      </div>

      {open.has('individual') && (
        <div className={styles.body}>
          <IndividualResponsesAccordion responses={response.responses} />
        </div>
      )}
      {open.has('critique') && (
        <div className={styles.body}>
          <CritiquesAccordion critiques={response.critiques} />
        </div>
      )}
      {open.has('revisions') && (
        <div className={styles.body}>
          <RevisionsAccordion revisions={response.revisions} />
        </div>
      )}
      {open.has('verification') && (
        <div className={styles.body}>
          <DisagreementNotice
            disagreement_level={response.disagreement_level}
            disagreement_reason={response.disagreement_reason}
            disagreement_evidence={response.disagreement_evidence}
          />
          <CodeVerificationPanel generatedTests={response.generated_tests} verifications={response.code_verifications} />
          <CalculationVerificationPanel
            referenceCalculation={response.reference_calculation}
            verifications={response.calculation_verifications}
          />
          <FactSearchPanel results={response.fact_search_results} />
        </div>
      )}
    </div>
  );
}
