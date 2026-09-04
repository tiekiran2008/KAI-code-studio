import { fetchClient } from './fetchClient';

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type FixValidationStatus = 'pending' | 'valid' | 'invalid';
export type FixUserDecision = 'pending' | 'accepted' | 'rejected';
export type FixApplicationStatus = 'not_applied' | 'applying' | 'applied' | 'stale' | 'apply_failed';
export type VerificationStatus = 'not_run' | 'passed' | 'failed' | 'unsupported' | 'source_changed';
export type SandboxVerificationStatus = 'not_run' | 'passed' | 'failed' | 'timed_out' | 'sandbox_unavailable' | 'execution_error' | 'unsupported' | 'source_changed';

export interface SandboxVerificationResult {
  status: SandboxVerificationStatus;
  verification_type: string;
  test_framework: string;
  command_label: string;
  exit_code?: number | null;
  duration_ms: number;
  tests_total?: number | null;
  tests_passed?: number | null;
  tests_failed?: number | null;
  tests_skipped?: number | null;
  stdout_summary: string;
  stderr_summary: string;
  timed_out: boolean;
  resource_limit_hit: boolean;
  verified_at?: string | null;
  verified_hash?: string | null;
  message?: string | null;
  error_details?: string | null;
}
export type CheckStatus = 'passed' | 'failed' | 'skipped' | 'unsupported';

export interface VerificationCheck {
  name: string;
  status: CheckStatus;
  message: string;
  line_number?: number | null;
  column?: number | null;
}

export interface StaticVerificationResult {
  status: VerificationStatus;
  language?: string | null;
  verified_at?: string | null;
  verified_hash?: string | null;
  duration_ms?: number | null;
  checks: VerificationCheck[];
  errors: string[];
  warnings: string[];
  message?: string | null;
}

export type GitCommitStatus =
  | 'committed'
  | 'already_committed'
  | 'stale_source'
  | 'not_git_repository'
  | 'dirty_conflict'
  | 'failed';

export interface GitCommitResult {
  status: GitCommitStatus;
  branch_name?: string | null;
  commit_sha?: string | null;
  committed_at?: string | null;
  file_path?: string | null;
  commit_message?: string | null;
  base_branch?: string | null;
  base_commit_sha?: string | null;
  message?: string | null;
  error_details?: string | null;
}

export type GitPushStatus =
  | 'pushed'
  | 'already_pushed'
  | 'no_remote'
  | 'remote_mismatch'
  | 'git_state_changed'
  | 'auth_required'
  | 'push_rejected'
  | 'remote_unavailable'
  | 'failed';

export interface GitPushResult {
  status: GitPushStatus;
  remote_name?: string | null;
  branch_name?: string | null;
  commit_sha?: string | null;
  remote_url_masked?: string | null;
  pushed_at?: string | null;
  message?: string | null;
  error_details?: string | null;
}

export type GitPullRequestStatus =
  | 'created'
  | 'already_exists'
  | 'auth_required'
  | 'permission_denied'
  | 'remote_branch_missing'
  | 'git_state_changed'
  | 'rate_limited'
  | 'unavailable'
  | 'failed';

export interface GitPullRequestResult {
  status: GitPullRequestStatus;
  pr_number?: number | null;
  pr_url?: string | null;
  title?: string | null;
  body?: string | null;
  head_branch?: string | null;
  base_branch?: string | null;
  created_at?: string | null;
  message?: string | null;
  error_details?: string | null;
}

export interface FixSuggestion {
  finding_index: number;
  file_path: string;
  original_code: string;
  proposed_code: string;
  explanation: string;
  diff: string;
  confidence_score: number;
  validation_status: FixValidationStatus;
  user_decision: FixUserDecision;
  application_status?: FixApplicationStatus;
  applied_at?: string | null;
  application_error?: string | null;
  previous_hash?: string | null;
  new_hash?: string | null;
  language?: string | null;
  validation_message?: string | null;
  static_verification?: StaticVerificationResult | null;
  test_verification?: SandboxVerificationResult | null;
  git_commit?: GitCommitResult | null;
  git_push?: GitPushResult | null;
  git_pull_request?: GitPullRequestResult | null;
}

export interface ReviewFinding {
  issue: string;
  severity: FindingSeverity;
  explanation: string;
  suggested_fix?: string;
  confidence_score: number;
  file_path?: string;
  line_number?: number;
  fix_suggestion?: FixSuggestion | null;
}

export type RefactoringCategory =
  | 'complexity'
  | 'duplication'
  | 'naming'
  | 'coupling'
  | 'cohesion'
  | 'solid'
  | 'patterns'
  | 'dead_code'
  | 'structure'
  | 'error_handling'
  | 'async'
  | 'god_object'
  | 'feature_envy'
  | 'smells';

export interface PerformanceFinding {
  issue: string;
  severity: FindingSeverity;
  estimated_impact?: string;
  file_path?: string;
  line_number?: number;
  root_cause?: string;
  suggested_optimization?: string;
  expected_performance_gain?: string;
  confidence_score: number;
}

export interface PerformanceRecommendation {
  title: string;
  description: string;
  impact_estimate?: string;
}

export interface PerformanceData {
  performance_score: number | null;
  performance_findings: PerformanceFinding[];
  performance_recommendations: PerformanceRecommendation[];
  estimated_cpu_savings: number;
  estimated_memory_savings: number;
  estimated_latency_improvement: number;
}

export interface RefactoringFinding {
  refactoring_type: string;
  priority: FindingSeverity;
  category: RefactoringCategory;
  file_path?: string;
  line_number?: number;
  explanation: string;
  current_problem?: string;
  suggested_refactoring?: string;
  before_preview?: string;
  after_preview?: string;
  benefits: string[];
  risks: string[];
  estimated_effort_hours: number;
  confidence_score: number;
}

export interface RefactoringData {
  refactoring_findings: RefactoringFinding[];
  refactoring_priority: FindingSeverity | null;
  estimated_refactoring_effort: number;
  estimated_maintainability_improvement: number;
  estimated_technical_debt_reduction: number;
  estimated_complexity_reduction: number;
}

export type ArchitectureCategory =
  | 'architecture'
  | 'clean_architecture'
  | 'coupling'
  | 'cohesion'
  | 'solid'
  | 'patterns'
  | 'technical_debt'
  | 'complexity'
  | 'documentation'
  | 'testability'
  | 'layer_violation'
  | 'modularity';

export interface ArchitectureFinding {
  category: ArchitectureCategory;
  severity: FindingSeverity;
  priority: FindingSeverity;
  file_path?: string;
  line_number?: number;
  explanation: string;
  root_cause: string;
  business_impact: string;
  recommendation: string;
  estimated_effort_hours: number;
  confidence_score: number;
}

export interface LayerDependencyViolation {
  source_layer: string;
  target_layer: string;
  source_file: string;
  target_file: string;
  description: string;
}

export interface HotspotFile {
  file_path: string;
  complexity_score: number;
  technical_debt_hours: number;
  issue_count: number;
}

export interface DependencyAnalysisResult {
  layer_violations?: LayerDependencyViolation[];
  circular_dependencies?: string[];
  hotspot_files?: HotspotFile[];
}

export interface ArchitectureData {
  architecture_findings: ArchitectureFinding[];
  overall_health_score: number;
  architecture_score: number;
  maintainability_score: number;
  technical_debt_score: number;
  complexity_score: number;
  documentation_score: number;
  modularity_score: number;
  testability_score: number;
  dependency_analysis: DependencyAnalysisResult;
}

export interface CodeReview {
  id: string;
  repository_id: string;
  user_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  progress_percent?: number;
  current_stage?: string;
  progress_message?: string;
  findings: ReviewFinding[];

  confidence_score: number;
  duration_ms?: number;
  performance_score?: number | null;
  performance_findings?: PerformanceFinding[];
  performance_recommendations?: PerformanceRecommendation[];
  estimated_cpu_savings?: number;
  estimated_memory_savings?: number;
  estimated_latency_improvement?: number;
  refactoring_findings?: RefactoringFinding[];
  refactoring_priority?: FindingSeverity | null;
  estimated_refactoring_effort?: number;
  estimated_maintainability_improvement?: number;
  estimated_technical_debt_reduction?: number;
  estimated_complexity_reduction?: number;
  architecture_findings?: ArchitectureFinding[];
  overall_health_score?: number;
  architecture_score?: number;
  maintainability_score?: number;
  technical_debt_score?: number;
  complexity_score?: number;
  documentation_score?: number;
  modularity_score?: number;
  testability_score?: number;
  dependency_analysis?: DependencyAnalysisResult;
  created_at: string;
  updated_at?: string;
}

export interface ReviewConfigParams {
  strictness: 'low' | 'medium' | 'high';
  codeQuality?: boolean;
  documentation?: boolean;
  architecture?: boolean;
  security?: boolean;
  performance?: boolean;
}

export interface StartReviewParams {
  repository_id: string;
  files?: string[];
  config?: ReviewConfigParams;
}


export const reviewsApi = {
  async startReview(data: StartReviewParams): Promise<{ message: string; review_id: string }> {
    return fetchClient.post('/reviews/start', data);
  },

  async cancelReview(id: string): Promise<{ message: string; status: string; review_id: string }> {
    return fetchClient.post(`/reviews/${id}/cancel`);
  },

  async getReview(id: string): Promise<CodeReview> {
    return fetchClient.get(`/reviews/${id}`);
  },

  async listReviews(params?: { repository_id?: string; status?: string; skip?: number; limit?: number }): Promise<CodeReview[]> {
    return fetchClient.get('/reviews', { params });
  },

  async getReviewHistory(repositoryId: string, skip = 0, limit = 50): Promise<CodeReview[]> {
    return fetchClient.get(`/reviews/history/${repositoryId}`, { params: { skip, limit } });
  },

  async getPerformanceData(reviewId: string): Promise<PerformanceData> {
    return fetchClient.get(`/reviews/${reviewId}/performance`);
  },

  async getRefactoringData(reviewId: string): Promise<RefactoringData> {
    return fetchClient.get(`/reviews/${reviewId}/refactoring`);
  },

  async getArchitectureData(reviewId: string): Promise<ArchitectureData> {
    return fetchClient.get(`/reviews/${reviewId}/architecture`);
  },

  async deleteReview(id: string): Promise<void> {
    return fetchClient.delete(`/reviews/${id}`);
  },

  async generateFix(reviewId: string, findingIndex: number): Promise<{ fix_suggestion: FixSuggestion; cached: boolean }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix`);
  },

  async acceptFix(reviewId: string, findingIndex: number): Promise<{ fix_suggestion: FixSuggestion }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/accept`);
  },

  async rejectFix(reviewId: string, findingIndex: number): Promise<{ fix_suggestion: FixSuggestion }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/reject`);
  },

  async applyFix(reviewId: string, findingIndex: number): Promise<{ fix_suggestion: FixSuggestion; idempotent: boolean }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/apply`);
  },

  async verifyFix(reviewId: string, findingIndex: number): Promise<{ verification: StaticVerificationResult; fix_suggestion: FixSuggestion }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/verify`);
  },

  async verifyFixTests(reviewId: string, findingIndex: number): Promise<{ verification: SandboxVerificationResult; fix_suggestion: FixSuggestion }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/verify-tests`);
  },

  async createFixCommit(reviewId: string, findingIndex: number): Promise<{ git_commit: GitCommitResult; fix_suggestion: FixSuggestion }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/git/commit`);
  },

  async pushFixBranch(reviewId: string, findingIndex: number): Promise<{ git_push: GitPushResult; fix_suggestion: FixSuggestion }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/git/push`);
  },

  async createFixPullRequest(reviewId: string, findingIndex: number): Promise<{ git_pull_request: GitPullRequestResult; fix_suggestion: FixSuggestion }> {
    return fetchClient.post(`/reviews/${reviewId}/findings/${findingIndex}/fix/git/pull-request`);
  },
};


