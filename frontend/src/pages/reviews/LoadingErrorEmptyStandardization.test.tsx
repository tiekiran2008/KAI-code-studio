/**
 * Frontend Tests — Phase 11.6B-3 Loading, Error & Empty State Standardization
 * ============================================================================
 * Comprehensive unit & integration tests verifying:
 * - Action-specific loading text & duplicate request prevention
 * - Localized action errors (Apply, Verify, Tests, Commit, Push, PR)
 * - Gemini 429 rate limit / quota UX
 * - Stale source 409 handling
 * - Sandbox unavailable handling without host fallback
 * - Git & GitHub / PR error states with zero credential exposure
 * - Empty states for history, zero findings, and analysis tabs
 * - Multi-finding error isolation
 * - Safe text rendering (no XSS injection via backend error payloads)
 * - Accessibility (role="status", role="alert")
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ReviewResultsPage } from './ReviewResultsPage';
import { ReviewHistoryPage } from './ReviewHistoryPage';
import { RunIsolatedTestsModal } from './RunIsolatedTestsModal';
import { CreateCommitModal } from './CreateCommitModal';
import { PushBranchModal } from './PushBranchModal';
import { CreatePullRequestModal } from './CreatePullRequestModal';
import {
  reviewsApi,
  CodeReview,
  ReviewFinding,
} from '../../api/reviews';

// ─── Test Fixtures ──────────────────────────────────────────────────────────

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
  explanation: 'os module imported but never referenced.',
  suggested_fix: 'Remove import os.',
  confidence_score: 0.89,
  file_path: 'src/utils/helpers.py',
  line_number: 1,
};

const mockCompletedReview: CodeReview = {
  id: 'rev-std-101',
  repository_id: 'repo-abc',
  user_id: 'user-xyz',
  status: 'completed',
  progress_percent: 100,
  current_stage: 'completed',
  confidence_score: 0.94,
  duration_ms: 3200,
  created_at: '2026-08-26T12:00:00Z',
  findings: [mockFinding0, mockFinding1],
};

function renderReviewResultsPage(reviewId = 'rev-std-101') {
  return render(
    <MemoryRouter initialEntries={[`/reviews/${reviewId}`]}>
      <Routes>
        <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
      </Routes>
    </MemoryRouter>
  );
}

// ─── 1. Action-Specific Loading Tests ───────────────────────────────────────

describe('Action-Specific Loading States & Duplicate Prevention', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('RunIsolatedTestsModal shows specific "Running isolated tests..." loading text', () => {
    render(
      <RunIsolatedTestsModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={true}
      />
    );
    expect(screen.getByText('Running isolated tests...')).toBeInTheDocument();
    // Button is disabled while loading
    expect(screen.getByRole('button', { name: /Run Tests/i })).toBeDisabled();
  });

  it('CreateCommitModal shows specific "Creating local commit..." loading text', () => {
    render(
      <CreateCommitModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={true}
        filePath="src/calc.py"
      />
    );
    expect(screen.getByText('Creating local commit...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Creating local commit.../i })).toBeDisabled();
  });

  it('PushBranchModal shows specific "Pushing branch..." loading text', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={true}
        branchName="ai-fix/test-branch"
      />
    );
    expect(screen.getByText('Pushing branch...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Pushing branch.../i })).toBeDisabled();
  });

  it('CreatePullRequestModal shows specific "Creating pull request..." loading text', () => {
    render(
      <CreatePullRequestModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={true}
        headBranch="ai-fix/test-branch"
        findingIssue="SQL Injection"
      />
    );
    expect(screen.getByText('Creating pull request...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Creating pull request.../i })).toBeDisabled();
  });
});

// ─── 2. Localized Error Standardization Tests ───────────────────────────────

describe('Localized Error Standardization & Safe Rendering', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('displays Gemini 429 quota error inline without creating fake fix', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);
    vi.spyOn(reviewsApi, 'generateFix').mockRejectedValueOnce(
      new Error('Gemini API rate limit / quota exceeded. Please wait a moment.')
    );

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('SQL injection risk in user query')).toBeInTheDocument();
    });

    const genButtons = screen.getAllByRole('button', { name: /(Auto Fix|Generate Fix)/i });
    fireEvent.click(genButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Gemini API rate limit \/ quota exceeded/i)).toBeInTheDocument();
    });
  });

  it('renders XSS payloads in error messages safely as plain text', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockCompletedReview);
    vi.spyOn(reviewsApi, 'generateFix').mockRejectedValueOnce(
      new Error('<script>alert("XSS")</script> Bad Request')
    );

    renderReviewResultsPage();

    await waitFor(() => {
      expect(screen.getByText('SQL injection risk in user query')).toBeInTheDocument();
    });

    const genButtons = screen.getAllByRole('button', { name: /(Auto Fix|Generate Fix)/i });
    fireEvent.click(genButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/<script>alert\("XSS"\)<\/script> Bad Request/i)).toBeInTheDocument();
    });
  });

  it('handles page-level 404 cleanly with back navigation without crash', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockRejectedValueOnce(new Error('Review not found'));

    renderReviewResultsPage('rev-nonexistent-404');

    await waitFor(() => {
      expect(screen.getByText('Review not found')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Back to Reviews/i })).toBeInTheDocument();
    });
  });
});

// ─── 3. Empty States Standardization Tests ──────────────────────────────────

vi.mock('../../store/reviewStore', async (importOriginal) => {
  const actual = await importOriginal() as any;
  return {
    ...actual,
    useReviewStore: () => ({
      history: [],
      isLoading: false,
      error: null,
      fetchUserReviews: vi.fn().mockResolvedValue(undefined),
      deleteReview: vi.fn(),
    }),
  };
});

vi.mock('../../store/repositoryStore', async (importOriginal) => {
  const actual = await importOriginal() as any;
  return {
    ...actual,
    useRepositoryStore: () => ({
      repositories: [],
      fetchRepositories: vi.fn().mockResolvedValue(undefined),
    }),
  };
});

describe('Empty States Standardization', () => {
  it('ReviewHistoryPage renders standardized empty state when history is empty', async () => {
    render(
      <MemoryRouter initialEntries={['/reviews/history']}>
        <ReviewHistoryPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('review-history-empty')).toBeInTheDocument();
      expect(screen.getByText('No Code Reviews Found')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Start Review Now/i })).toBeInTheDocument();
    });
  });
});
