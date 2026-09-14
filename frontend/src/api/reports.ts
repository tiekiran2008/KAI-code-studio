import { fetchClient, buildApiUrl, getAuthToken } from './fetchClient';

// ── Shared types ────────────────────────────────────────────────────────────

export type ExportFormat = 'markdown' | 'html' | 'json' | 'sarif' | 'pdf';

export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface ReportMetrics {
  overall_health_score:   number;
  risk_score:             number;
  security_score:         number;
  performance_score:      number;
  architecture_score:     number;
  maintainability_score:  number;
  technical_debt_score:   number;
  complexity_score:       number;
  documentation_score:    number;
  testability_score:      number;
  confidence_score?:      number;
}

export interface ActionItem {
  priority:               string;
  title:                  string;
  description:            string;
  category:               string;
  estimated_effort_hours: number;
  agent_source:           string;
}

export interface RepositorySnapshot {
  repository_id:    string;
  repository_name?: string;
  generated_at?:    string;
}

export interface ReportContent {
  report_id?:              string;
  review_id?:              string;
  repository_id?:          string;
  repository_name?:        string;
  generated_at?:           string;
  report_version?:         string;
  executive_summary?:      string;
  repository_overview?:    Record<string, any>;
  code_review_findings?:   any[];
  code_review_summary?:    string;
  security_findings?:      any[];
  security_summary?:       string;
  performance_findings?:   any[];
  performance_recommendations?: any[];
  performance_summary?:    string;
  refactoring_findings?:   any[];
  refactoring_summary?:    string;
  architecture_findings?:  any[];
  dependency_analysis?:    Record<string, any>;
  architecture_summary?:   string;
  metrics?:                ReportMetrics;
  total_technical_debt_hours?: number;
  tech_debt_breakdown?:    Record<string, number>;
  tech_debt_summary?:      string;
  complexity_summary?:     string;
  maintainability_summary?: string;
  hotspot_files?:          any[];
  risk_level?:             string;
  risk_factors?:           string[];
  risk_summary?:           string;
  action_items?:           ActionItem[];
  future_improvements?:    string[];
  future_improvements_summary?: string;
}

export interface EngineeringReport {
  id:                      string;
  repository_id:           string;
  review_id?:              string;
  user_id:                 string;
  title:                   string;
  version:                 string;
  status:                  ReportStatus;
  overall_health_score:    number;
  risk_score:              number;
  security_score:          number;
  performance_score:       number;
  architecture_score:      number;
  maintainability_score:   number;
  technical_debt_score:    number;
  complexity_score:        number;
  documentation_score:     number;
  testability_score:       number;
  repository_snapshot:     RepositorySnapshot;
  export_formats:          ExportFormat[];
  report_content:          ReportContent;
  created_at:              string;
  updated_at?:             string;
}

export interface ReportScores {
  overall_health_score:    number;
  risk_score:              number;
  security_score:          number;
  performance_score:       number;
  architecture_score:      number;
  maintainability_score:   number;
  technical_debt_score:    number;
  complexity_score:        number;
  documentation_score:     number;
  testability_score:       number;
}

export interface ReportComparisonSide {
  id:             string;
  created_at:     string;
  scores:         ReportScores;
  finding_counts: Record<string, number>;
}

export interface ReportComparisonResult {
  report_a:             ReportComparisonSide;
  report_b:             ReportComparisonSide;
  score_deltas:         Record<string, number>;
  finding_count_deltas: Record<string, number>;
  improved_metrics:     string[];
  degraded_metrics:     string[];
}

export interface GenerateReportParams {
  repository_id: string;
  review_id?:    string;
  title?:        string;
}

// ── API client ───────────────────────────────────────────────────────────────

export const reportsApi = {
  async generateReport(data: GenerateReportParams): Promise<EngineeringReport> {
    return fetchClient.post('/reports/generate', data);
  },

  async listReports(skip = 0, limit = 50): Promise<EngineeringReport[]> {
    return fetchClient.get('/reports', { params: { skip, limit } });
  },

  async getReport(id: string): Promise<EngineeringReport> {
    return fetchClient.get(`/reports/${id}`);
  },

  async deleteReport(id: string): Promise<void> {
    return fetchClient.delete(`/reports/${id}`);
  },

  async exportReport(id: string, format: ExportFormat): Promise<Blob> {
    const url = buildApiUrl(`/reports/${id}/export?format=${format}`);
    const token = await getAuthToken();
    const res = await fetch(url, {
      method:  'GET',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
    return res.blob();
  },

  async compareReports(
    report_id_a: string,
    report_id_b: string,
  ): Promise<ReportComparisonResult> {
    return fetchClient.post('/reports/compare', { report_id_a, report_id_b });
  },
};
