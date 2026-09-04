import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ReviewResultsPage } from './ReviewResultsPage';
import { reviewsApi, CodeReview, ReviewFinding, FixSuggestion } from '../../api/reviews';

const mockFinding0: ReviewFinding = {
  issue: 'SQL injection risk in user query',
  severity: 'critical',
  explanation: 'Query string concatenation allows unsanitized user inputs.',
  suggested_fix: 'Use parameterized queries with SQLAlchemy bindings.',
  confidence_score: 0.98,
  file_path: 'src/repositories/user_repo.py',
  line_number: 42,
};

const mockFinding1: ReviewFinding = {
  issue: 'Unused import os',
  severity: 'low',
  explanation: 'os module imported but never referenced in module scope.',
  suggested_fix: 'Remove import os.',
  confidence_score: 0.89,
  file_path: 'src/utils/helpers.py',
  line_number: 1,
  fix_suggestion: {
    finding_index: 1,
    file_path: 'src/utils/helpers.py',
    original_code: 'import os\nimport sys',
    proposed_code: 'import sys',
    explanation: 'Removed unused import os.',
    diff: '--- a/src/utils/helpers.py\n+++ b/src/utils/helpers.py\n@@ -1,2 +1 @@\n-import os\n import sys',
    confidence_score: 0.95,
    validation_status: 'valid',
    user_decision: 'accepted',
  },
};

const mockCompletedReview: CodeReview = {
  id: 'rev-test-101',
  repository_id: 'repo-abc',
  user_id: 'user-xyz',
  status: 'completed',
  progress_percent: 100,
  current_stage: 'completed',
  confidence_score: 0.94,
  duration_ms: 3200,
  created_at: '2026-08-23T12:00:00Z',
  findings: [mockFinding0, mockFinding1],
};

const mockGeneratedFix: FixSuggestion = {
  finding_index: 0,
  file_path: 'src/repositories/user_repo.py',
  original_code: 'query = f"SELECT * FROM users WHERE id = {user_id}"',
  proposed_code: 'query = select(User).where(User.id == user_id)',
  explanation: 'Replaced f-string query with parameterized SQLAlchemy expression.',
  diff: '--- a/src/repositories/user_repo.py\n+++ b/src/repositories/user_repo.py\n@@ -1 +1 @@\n-query = f"SELECT * FROM users WHERE id = {user_id}"\n+query = select(User).where(User.id == user_id)',
  confidence_score: 0.97,
  validation_status: 'valid',
  user_decision: 'pending',
};

const renderReviewResultsPage = () => {
  return render(
    <MemoryRouter initialEntries={['/reviews/rev-test-101/results']}>
      <Routes>
        <Route path="/reviews/:reviewId/results" element={<ReviewResultsPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('ReviewResultsPage Fix Suggestion End-to-End Interactions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "Generate Fix" for un-fixed findings and "View Fix" for persisted suggestions', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('SQL injection risk in user query')).toBeInTheDocument();
    });

    // Finding 0 has no fix_suggestion -> shows "Generate Fix"
    expect(screen.getByRole('button', { name: /Generate Fix/i })).toBeInTheDocument();

    // Finding 1 has persisted fix_suggestion -> shows "View Fix" and "Accepted" badge
    expect(screen.getByRole('button', { name: /View Fix/i })).toBeInTheDocument();
    expect(screen.getByText('Accepted')).toBeInTheDocument();
  });

  it('clicking Generate Fix invokes API and automatically opens FixSuggestionModal', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);
    vi.spyOn(reviewsApi, 'generateFix').mockResolvedValueOnce({
      fix_suggestion: mockGeneratedFix,
      cached: false,
    });

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate Fix/i })).toBeInTheDocument();
    });

    const generateBtn = screen.getByRole('button', { name: /Generate Fix/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(reviewsApi.generateFix).toHaveBeenCalledWith('rev-test-101', 0);
      // Modal should open with the generated fix
      expect(screen.getByText('Automated Fix Suggestion')).toBeInTheDocument();
      expect(screen.getByText(/Replaced f-string query/i)).toBeInTheDocument();
    });
  });

  it('clicking View Fix on persisted suggestion opens modal without calling generateFix', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);
    const generateSpy = vi.spyOn(reviewsApi, 'generateFix');

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /View Fix/i })).toBeInTheDocument();
    });

    const viewBtn = screen.getByRole('button', { name: /View Fix/i });
    fireEvent.click(viewBtn);

    expect(screen.getByText('Automated Fix Suggestion')).toBeInTheDocument();
    expect(screen.getByText(/Removed unused import os/i)).toBeInTheDocument();
    // Verify generateFix was NOT called
    expect(generateSpy).not.toHaveBeenCalled();
  });

  it('displays inline error when fix generation fails without breaking finding list', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);
    vi.spyOn(reviewsApi, 'generateFix').mockRejectedValueOnce(
      new Error('LLM quota exceeded: 429 RESOURCE_EXHAUSTED')
    );

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Generate Fix/i })).toBeInTheDocument();
    });

    const generateBtn = screen.getByRole('button', { name: /Generate Fix/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText(/LLM quota exceeded: 429 RESOURCE_EXHAUSTED/i)).toBeInTheDocument();
    });

    // Both findings remain intact
    expect(screen.getByText('SQL injection risk in user query')).toBeInTheDocument();
    expect(screen.getByText('Unused import os')).toBeInTheDocument();
  });

  it('maintains independent state across multiple findings', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('SQL injection risk in user query')).toBeInTheDocument();
      expect(screen.getByText('Unused import os')).toBeInTheDocument();
    });

    // Finding 0: pending generation
    expect(screen.getByRole('button', { name: /Generate Fix/i })).toBeInTheDocument();
    // Finding 1: already accepted
    expect(screen.getByRole('button', { name: /View Fix/i })).toBeInTheDocument();
  });

  it('33. Refresh persistence: reviews with applied suggestions render Applied badge immediately', async () => {
    const reviewWithApplied: CodeReview = {
      ...mockCompletedReview,
      findings: [
        {
          ...mockFinding0,
          fix_suggestion: {
            ...mockGeneratedFix,
            user_decision: 'accepted',
            application_status: 'applied',
            applied_at: '2026-08-25T08:00:00Z',
          },
        },
        mockFinding1,
      ],
    };

    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(reviewWithApplied);

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('SQL injection risk in user query')).toBeInTheDocument();
    });

    // Finding 0 shows Applied badge
    expect(screen.getByText('Applied')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /View Fix/i }).length).toBe(2);
  });

  it('34. Multiple findings independence: applying finding 0 does not alter finding 1 state', async () => {
    const reviewWithTwoAccepted: CodeReview = {
      ...mockCompletedReview,
      findings: [
        {
          ...mockFinding0,
          fix_suggestion: {
            ...mockGeneratedFix,
            user_decision: 'accepted',
            application_status: 'not_applied',
          },
        },
        {
          ...mockFinding1,
          fix_suggestion: {
            ...mockFinding1.fix_suggestion!,
            user_decision: 'accepted',
            application_status: 'not_applied',
          },
        },
      ],
    };

    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(reviewWithTwoAccepted);
    vi.spyOn(reviewsApi, 'applyFix').mockResolvedValueOnce({
      fix_suggestion: {
        ...mockGeneratedFix,
        user_decision: 'accepted',
        application_status: 'applied',
        applied_at: '2026-08-25T08:30:00Z',
      },
      idempotent: false,
    });

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /View Fix/i }).length).toBe(2);
    });

    // Open finding 0
    const viewButtons = screen.getAllByRole('button', { name: /View Fix/i });
    fireEvent.click(viewButtons[0]);

    // Click Apply Suggestion in modal
    const applyBtn = screen.getByRole('button', { name: /Apply Suggestion/i });
    fireEvent.click(applyBtn);

    // Confirm Apply
    const confirmBtn = screen.getByRole('button', { name: /Apply Fix/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(reviewsApi.applyFix).toHaveBeenCalledWith('rev-test-101', 0);
    });

    // Close modal
    const closeBtn = screen.getByLabelText(/Close modal/i);
    fireEvent.click(closeBtn);

    // Finding 0 should now show Applied
    expect(screen.getByText('Applied')).toBeInTheDocument();
    // Finding 1 should still show Accepted (not Applied)
    expect(screen.getByText('Accepted')).toBeInTheDocument();
  });

  it('renders clean empty state when completed review has zero findings', async () => {
    const emptyReview: CodeReview = {
      ...mockCompletedReview,
      findings: [],
    };
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(emptyReview);
    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('0 Findings')).toBeInTheDocument();
      expect(screen.getByText('No code quality issues found.')).toBeInTheDocument();
    });
  });

  it('renders clean failure alert banner when review execution failed', async () => {
    const failedReview: CodeReview = {
      ...mockCompletedReview,
      status: 'failed',
    };
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(failedReview);
    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('Code Review Execution Failed')).toBeInTheDocument();
    });
  });

  it('renders clean cancellation banner when review was cancelled', async () => {
    const cancelledReview: CodeReview = {
      ...mockCompletedReview,
      status: 'cancelled',
    };
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(cancelledReview);
    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('Code Review Cancelled')).toBeInTheDocument();
    });
  });

  it('renders FixWorkflowStepper inside expanded FindingRow with no mutation calls', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('SQL injection risk in user query')).toBeInTheDocument();
    });

    // Expand finding 1 (which has fix_suggestion)
    const expandButtons = screen.getAllByLabelText(/Expand finding details/i);
    fireEvent.click(expandButtons[1]);

    // Stepper should render
    expect(screen.getByTestId('fix-workflow-stepper-compact')).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
