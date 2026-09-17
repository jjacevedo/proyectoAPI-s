export type TaskTypeBreakdown = {
  task_type: string;
  count: number;
  avg_tokens: number;
  avg_cost_usd: number | null;
  avg_latency_ms: number;
};

export type ComplexityBreakdown = {
  complexity: string;
  count: number;
  avg_tokens: number;
  avg_cost_usd: number | null;
  avg_latency_ms: number;
};

export type VerificationStats = {
  code_verification_pass_rate: number | null;
  calculation_verification_pass_rate: number | null;
  fact_search_result_count: number;
};

export type EvaluationStats = {
  total_evaluations: number;
  multi_wins: number;
  single_wins: number;
  ties: number;
  judge_unavailable: number;
  avg_token_delta: number | null;
  avg_cost_delta_usd: number | null;
  avg_latency_delta_ms: number | null;
};

export type DashboardStats = {
  total_requests: number;
  total_tokens: number;
  total_cost_estimated_usd: number | null;
  avg_latency_ms: number | null;
  by_task_type: TaskTypeBreakdown[];
  by_complexity: ComplexityBreakdown[];
  verification: VerificationStats;
  evaluation: EvaluationStats;
};
