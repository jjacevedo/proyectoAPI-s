import type { ChatResponse } from '@/types/chat';

type Props = Pick<ChatResponse, 'disagreement_level' | 'disagreement_reason' | 'disagreement_evidence'>;

export function DisagreementNotice({ disagreement_level, disagreement_reason, disagreement_evidence }: Props) {
  if (disagreement_level === 'not_applicable') return null;

  return (
    <div className={`card meta ${disagreement_level === 'disagreement' ? 'error' : ''}`}>
      Desacuerdo: {disagreement_level} ({disagreement_reason})
      {disagreement_evidence.length > 0 && (
        <ul>
          {disagreement_evidence.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
