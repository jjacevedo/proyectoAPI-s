export type ProviderResponse = {
  provider: string;
  model: string;
  content: string | null;
  tokens: number;
  latency_ms: number;
  cost_estimated_usd: number | null;
  error: string | null;
};

export type CritiqueResponse = {
  provider: string;
  model: string;
  content: string | null;
  reviewed_providers: string[];
  tokens: number;
  latency_ms: number;
  cost_estimated_usd: number | null;
  error: string | null;
};

export type CodeVerificationResponse = {
  provider: string;
  model: string;
  passed: boolean;
  tests_run: number;
  tests_passed: number;
  tests_failed: number;
  stdout: string;
  stderr: string;
  error: string | null;
  timed_out: boolean;
};

export type ChatResponse = {
  final_answer: string;
  responses: ProviderResponse[];
  critiques: CritiqueResponse[];
  revisions: ProviderResponse[];
  models_used: string[];
  total_tokens: number;
  total_cost_estimated_usd: number | null;
  latency_ms: number;
  complexity: string;
  routing_reason: string;
  task_type: string;
  disagreement_level: string;
  disagreement_reason: string;
  disagreement_evidence: string[];
  generated_tests: string | null;
  code_verifications: CodeVerificationResponse[];
};
