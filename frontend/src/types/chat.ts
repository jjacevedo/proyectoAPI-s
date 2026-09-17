export type ProviderResponse = {
  provider: string;
  model: string;
  content: string | null;
  tokens: number;
  latency_ms: number;
  cost_estimated_usd: number | null;
  error: string | null;
};

export type ChatResponse = {
  final_answer: string;
  responses: ProviderResponse[];
  models_used: string[];
  total_tokens: number;
  total_cost_estimated_usd: number | null;
  latency_ms: number;
  complexity: string;
  routing_reason: string;
};
