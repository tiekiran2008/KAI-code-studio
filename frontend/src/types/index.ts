// Core Domain Types for AI Software Engineering Platform

export type PermissionLevel = 'read_only' | 'restricted' | 'admin_only';
export type IndexingStatus = 'indexed' | 'indexing' | 'pending' | 'failed';
export type AgentType = 
  | 'supervisor'
  | 'planner'
  | 'context'
  | 'code_analysis'
  | 'bug_detection'
  | 'security_review'
  | 'performance'
  | 'documentation'
  | 'test_generation'
  | 'code_review'
  | 'evaluation';

export type MemoryType = 'short_term' | 'long_term' | 'repository' | 'episodic';

export type RepositoryProvider = 'github' | 'gitlab' | 'bitbucket' | 'local';

export interface LanguageStat {
  language: string;
  percentage: number;
  bytes: number;
}

export interface DetectedStack {
  language?: string;
  framework?: string;
  package_manager?: string;
  build_tool?: string;
  test_framework?: string;
}

export interface Repository {
  id: string;
  user_id?: string;
  workspace_id?: string;
  name: string;
  owner?: string;
  description?: string;
  url: string;
  provider?: RepositoryProvider;
  defaultBranch?: string;
  currentBranch?: string;
  default_branch?: string;
  current_branch?: string;
  branches: string[];
  indexingStatus: IndexingStatus;
  indexing_status?: IndexingStatus;
  chunksCount?: number;
  chunks_count?: number;
  lastIndexedAt?: string;
  last_indexed_at?: string;
  language?: string;
  language_stats?: LanguageStat[];
  detected_stack?: DetectedStack;
  repo_size_kb?: number;
  stars?: number;
  isLocal?: boolean;
  is_private?: boolean;
  created_at?: string;
  updated_at?: string;
}

export type RoleEnum = 'owner' | 'admin' | 'maintainer' | 'developer' | 'reviewer' | 'viewer';

export interface TeamMember {
  id: string;
  team_id: string;
  user_id: string;
  role: RoleEnum;
  email: string;
  name: string;
  avatar?: string;
  joined_at: string;
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  member_count: number;
  members: TeamMember[];
  created_at: string;
  updated_at: string;
}

export interface Invitation {
  id: string;
  team_id: string;
  team_name?: string;
  email: string;
  role: RoleEnum;
  token: string;
  status: 'pending' | 'accepted' | 'rejected' | 'expired';
  invited_by: string;
  expires_at: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  team_id: string;
  actor_id: string;
  action: string;
  target_type: string;
  target_id?: string;
  details_json: Record<string, any>;
  created_at: string;
}

export interface PermissionMatrixRow {
  permission: string;
  category: string;
  description: string;
  roles: Record<RoleEnum, boolean>;
}

export interface Project {
  id: string;
  user_id: string;
  workspace_id?: string;
  name: string;
  description?: string;
  status: 'active' | 'archived';
  repositories: Repository[];
  created_at: string;
  updated_at: string;
}

export interface ProjectDashboard {
  project: Project;
  total_repositories: number;
  indexed_repositories: number;
  failed_repositories: number;
  total_chunks: number;
  languages: string[];
}

export interface FileNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
  content?: string;
  language?: string;
  size?: number;
}

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet: string;
  score?: number;
}

export interface ToolCallTrace {
  tool_name: string;
  caller_agent: string;
  arguments: Record<string, any>;
  result?: any;
  success: boolean;
  latency_ms: number;
  error?: string;
  timestamp: string;
}

export interface AgentExecutionTrace {
  agent: AgentType;
  action: string;
  latency_ms: number;
  confidence?: number;
  output_summary?: string;
  details?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  citations?: Citation[];
  agentTraces?: AgentExecutionTrace[];
  toolCalls?: ToolCallTrace[];
  isStreaming?: boolean;
}

export interface ConversationSession {
  id: string;
  title: string;
  repositoryId?: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface MemoryRecord {
  id: string;
  userId: string;
  repositoryId?: string;
  memoryType: MemoryType;
  content: string;
  importanceScore: number;
  recencyBonus?: number;
  createdAt: string;
  updatedAt: string;
  techStack?: string[];
  isEncrypted: boolean;
}

export interface ToolMetadata {
  name: string;
  description: string;
  permissions: PermissionLevel;
  timeoutSeconds: number;
  retryMax: number;
  version: string;
  inputSchema: Record<string, any>;
}

export interface AnalyticsMetrics {
  retrievalLatencyP50: number;
  retrievalLatencyP95: number;
  retrievalLatencyP99: number;
  totalTokensUsed: number;
  agentExecutionsCount: number;
  toolInvocationsCount: number;
  memoryHitRate: number;
  activeSessionsCount: number;
  averageConfidence: number;
}

export interface LLMSettings {
  provider: 'gemini' | 'openai' | 'anthropic' | 'ollama';
  apiKey: string;
  modelName: string;
  temperature: number;
  maxTokens: number;
  baseUrl?: string;
}

export interface UserPreferences {
  theme: 'dark' | 'light' | 'system';
  preferredLanguage: string;
  codeEditorFontSize: number;
  autoFormatCode: boolean;
  enableStreamResponse: boolean;
  defaultAgentStrategy: 'auto' | 'planner_guided' | 'direct';
}

// ─── Phase 11.2 / 11.3 / 11.4 Fix Suggestion, Apply & Verification Types ─────

export type FixValidationStatus = 'pending' | 'valid' | 'invalid';
export type FixUserDecision = 'pending' | 'accepted' | 'rejected';
export type FixApplicationStatus = 'not_applied' | 'applying' | 'applied' | 'stale' | 'apply_failed';
export type VerificationStatus = 'not_run' | 'passed' | 'failed' | 'unsupported' | 'source_changed';
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
}


