import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ReportsPage } from './ReportsPage';
import { reportsApi } from '../../api/reports';
import type { EngineeringReport } from '../../api/reports';

// ── Mock reportsApi ───────────────────────────────────────────────────────────

vi.mock('../../api/reports', () => ({
  reportsApi: {
    listReports:    vi.fn(),
    getReport:      vi.fn(),
    deleteReport:   vi.fn(),
    exportReport:   vi.fn(),
    compareReports: vi.fn(),
  },
}));

// ── Test data ─────────────────────────────────────────────────────────────────

const makeReport = (overrides: Partial<EngineeringReport> = {}): EngineeringReport => ({
  id:                    'rpt-001',
  repository_id:         'repo-123',
  review_id:             'rev-001',
  user_id:               'user-001',
  title:                 'Engineering Report',
  version:               '1.0',
  status:                'completed',
  overall_health_score:  72.5,
  risk_score:            27.5,
  security_score:        65.0,
  performance_score:     70.0,
  architecture_score:    75.0,
  maintainability_score: 68.0,
  technical_debt_score:  65.0,
  complexity_score:      80.0,
  documentation_score:   85.0,
  testability_score:     78.0,
  repository_snapshot:   { repository_id: 'repo-123' },
  export_formats:        [],
  report_content: {
    executive_summary:   'Overall health is moderate.',
    risk_level:          'high',
    risk_factors:        ['SQL Injection'],
    total_technical_debt_hours: 12.5,
    tech_debt_breakdown: { security: 4.0, refactoring: 8.5 },
    action_items: [
      {
        priority: 'critical',
        title: 'Fix SQL Injection',
        description: 'Use parameterized queries.',
        category: 'security',
        estimated_effort_hours: 2.0,
        agent_source: 'security_review',
      },
    ],
    security_findings: [
      { severity: 'critical', issue: 'SQL Injection', explanation: 'Unsanitised input' },
    ],
    performance_findings:   [],
    refactoring_findings:   [],
    architecture_findings:  [],
    future_improvements:    ['Adopt parameterized queries'],
    future_improvements_summary: 'Focus on security hardening.',
    metrics: {
      overall_health_score: 72.5, risk_score: 27.5, security_score: 65.0,
      performance_score: 70.0, architecture_score: 75.0, maintainability_score: 68.0,
      technical_debt_score: 65.0, complexity_score: 80.0,
      documentation_score: 85.0, testability_score: 78.0,
    },
  },
  created_at: '2026-08-05T14:00:00Z',
  ...overrides,
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <ReportsPage />
    </MemoryRouter>
  );

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    vi.mocked(reportsApi.listReports).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText(/loading reports/i)).toBeInTheDocument();
  });

  it('renders page heading', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([]);
    renderPage();
    await waitFor(() => expect(screen.getByText('Engineering Reports')).toBeInTheDocument());
  });

  it('shows empty state when no reports', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([]);
    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/no engineering reports yet/i)).toBeInTheDocument()
    );
  });

  it('renders report list when reports exist', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() =>
      expect(screen.getByText('Engineering Report')).toBeInTheDocument()
    );
  });

  it('shows overall health score', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => {
      const scores = screen.getAllByText(/72/);
      expect(scores.length).toBeGreaterThan(0);
    });
  });

  it('shows HIGH RISK badge for high risk report', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() =>
      expect(screen.getByText('HIGH RISK')).toBeInTheDocument()
    );
  });

  it('shows summary stat cards', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Total Reports')).toBeInTheDocument();
      expect(screen.getByText('Avg Health Score')).toBeInTheDocument();
      expect(screen.getByText('High Risk Repos')).toBeInTheDocument();
    });
  });

  it('filter input filters by title', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([
      makeReport({ id: 'rpt-001', title: 'Alpha Report' }),
      makeReport({ id: 'rpt-002', title: 'Beta Report' }),
    ]);
    renderPage();
    await waitFor(() => screen.getByText('Alpha Report'));
    fireEvent.change(screen.getByPlaceholderText(/search by title/i), {
      target: { value: 'Alpha' },
    });
    expect(screen.getByText('Alpha Report')).toBeInTheDocument();
    expect(screen.queryByText('Beta Report')).not.toBeInTheDocument();
  });

  it('clicking View opens detail panel', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    const viewBtn = screen.getByRole('button', { name: /view/i });
    fireEvent.click(viewBtn);
    await waitFor(() =>
      expect(screen.getByText('Overall health is moderate.')).toBeInTheDocument()
    );
  });

  it('detail panel has section navigation', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    fireEvent.click(screen.getByRole('button', { name: /view/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /overview/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /action plan/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /security/i })).toBeInTheDocument();
    });
  });

  it('detail panel shows action items', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    fireEvent.click(screen.getByRole('button', { name: /view/i }));
    await waitFor(() => screen.getByText('Action Plan'));
    fireEvent.click(screen.getByText('Action Plan'));
    await waitFor(() =>
      expect(screen.getByText('Fix SQL Injection')).toBeInTheDocument()
    );
  });

  it('detail panel export toolbar renders all format buttons', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    fireEvent.click(screen.getByRole('button', { name: /view/i }));
    await waitFor(() => {
      expect(document.getElementById('export-btn-markdown') ||
        screen.getByText('Markdown')).toBeInTheDocument();
      expect(screen.getByText('SARIF')).toBeInTheDocument();
    });
  });

  it('closing detail panel removes it', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    fireEvent.click(screen.getByRole('button', { name: /view/i }));
    await waitFor(() => screen.getByText('Overall health is moderate.'));
    fireEvent.click(screen.getByRole('button', { name: /close panel/i }));
    await waitFor(() =>
      expect(screen.queryByText('Overall health is moderate.')).not.toBeInTheDocument()
    );
  });

  it('delete button calls API and removes report', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    vi.mocked(reportsApi.deleteReport).mockResolvedValue();
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    const deleteBtn = document.getElementById('delete-report-rpt-001')!;
    fireEvent.click(deleteBtn);
    await waitFor(() => {
      expect(reportsApi.deleteReport).toHaveBeenCalledWith('rpt-001');
    });
  });

  it('compare button disabled when fewer than 2 reports', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    const compareBtn = screen.getByRole('button', { name: /compare/i });
    expect(compareBtn).toBeDisabled();
  });

  it('compare button enabled with 2 or more reports', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([
      makeReport({ id: 'rpt-001' }),
      makeReport({ id: 'rpt-002' }),
    ]);
    renderPage();
    await waitFor(() => {
      const compareBtn = screen.getByRole('button', { name: /compare/i });
      expect(compareBtn).not.toBeDisabled();
    });
  });

  it('comparison modal opens when Compare clicked', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([
      makeReport({ id: 'rpt-001' }),
      makeReport({ id: 'rpt-002' }),
    ]);
    renderPage();
    await waitFor(() => screen.getAllByText('Engineering Report'));
    fireEvent.click(screen.getByRole('button', { name: /compare/i }));
    expect(screen.getByText('Compare Reports')).toBeInTheDocument();
  });

  it('refresh button re-fetches reports', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([makeReport()]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    const refreshBtn = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshBtn);
    await waitFor(() => expect(reportsApi.listReports).toHaveBeenCalledTimes(2));
  });

  it('shows error state when fetch fails', async () => {
    vi.mocked(reportsApi.listReports).mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    );
  });

  it('status filter hides non-matching reports', async () => {
    vi.mocked(reportsApi.listReports).mockResolvedValue([
      makeReport({ id: 'rpt-001', status: 'completed' }),
      makeReport({ id: 'rpt-002', title: 'Pending Report', status: 'pending' }),
    ]);
    renderPage();
    await waitFor(() => screen.getByText('Engineering Report'));
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'pending' } });
    expect(screen.getByText('Pending Report')).toBeInTheDocument();
    expect(screen.queryByText('Engineering Report')).not.toBeInTheDocument();
  });
});
