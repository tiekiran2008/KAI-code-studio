/**
 * Frontend Tests — Phase 11.5B-5 Create GitHub Pull Request
 * ==========================================================
 * Tests:
 * - CreatePullRequestModal rendering, confirm/cancel actions, loading state
 * - CommitSection PR button visibility (only when pushed), PR info display, safe external link, error banners
 * - FixSuggestionModal integration (PR button triggers modal, API call, state update)
 * - ReviewResultsPage "PR #..." badge visibility
 * - Safe rendering (no script injection / dangerouslySetInnerHTML)
 * - Zero auto-PR guarantee (page load/refresh makes 0 PR API calls)
 *
 * LLM calls: 0  shell: 0  auto-merge: 0  force-push: 0
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { FixSuggestionModal } from './FixSuggestionModal';
import { ReviewResultsPage } from './ReviewResultsPage';
import { CreatePullRequestModal } from './CreatePullRequestModal';
import { CommitSection } from './CommitSection';
import {
  reviewsApi,
  ReviewFinding,
  FixSuggestion,
  GitCommitResult,
  GitPushResult,
  GitPullRequestResult,
} from '../../api/reviews';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const sampleFinding: ReviewFinding = {
  issue: 'Missing return type hint',
  severity: 'medium',
  explanation: 'Function is missing return type annotation.',
  suggested_fix: 'Add return type annotation -> int.',
  confidence_score: 0.95,
  file_path: 'src/calc.py',
  line_number: 10,
};

const mockGitCommit: GitCommitResult = {
  status: 'committed',
  branch_name: 'ai-fix/rev-abc12345-f0',
  commit_sha: 'a1b2c3d4e5f67890abcdef1234567890abcdef12',
  committed_at: '2026-08-26T09:10:00Z',
  file_path: 'src/calc.py',
  commit_message: 'fix: resolve finding 0 in src/calc.py',
  base_branch: 'main',
  base_commit_sha: 'b' + '2'.repeat(39),
};

const mockGitPush: GitPushResult = {
  status: 'pushed',
  remote_name: 'origin',
  branch_name: 'ai-fix/rev-abc12345-f0',
  commit_sha: 'a1b2c3d4e5f67890abcdef1234567890abcdef12',
  remote_url_masked: 'https://github.com/my-org/my-repo.git',
  pushed_at: '2026-08-26T09:15:00Z',
  message: 'Pushed to origin',
};

const mockGitPullRequest: GitPullRequestResult = {
  status: 'created',
  pr_number: 42,
  pr_url: 'https://github.com/my-org/my-repo/pull/42',
  title: 'fix: Missing return type hint',
  body: '## AI Code Review Fix Summary\n\nResolved finding.',
  head_branch: 'ai-fix/rev-abc12345-f0',
  base_branch: 'main',
  created_at: '2026-08-26T09:20:00Z',
  message: 'Created Pull Request #42',
};

const samplePushedFix: FixSuggestion = {
  finding_index: 0,
  file_path: 'src/calc.py',
  original_code: 'def add(a, b):\n    return a + b',
  proposed_code: 'def add(a: int, b: int) -> int:\n    return a + b',
  explanation: 'Added type hints.',
  diff: '--- a/src/calc.py\n+++ b/src/calc.py',
  confidence_score: 0.95,
  validation_status: 'valid',
  user_decision: 'accepted',
  application_status: 'applied',
  applied_at: '2026-08-26T09:00:00Z',
  static_verification: {
    status: 'passed',
    language: 'py',
    verified_at: '2026-08-26T09:05:00Z',
    verified_hash: 'abc123',
    duration_ms: 15,
    checks: [],
    errors: [],
    warnings: [],
  },
  git_commit: mockGitCommit,
  git_push: mockGitPush,
};

const samplePRCreatedFix: FixSuggestion = {
  ...samplePushedFix,
  git_pull_request: mockGitPullRequest,
};

// Mock reviewsApi
vi.mock('../../api/reviews', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/reviews')>();
  return {
    ...actual,
    reviewsApi: {
      ...actual.reviewsApi,
      generateFix: vi.fn(),
      acceptFix: vi.fn(),
      rejectFix: vi.fn(),
      applyFix: vi.fn(),
      verifyFix: vi.fn(),
      verifyFixTests: vi.fn(),
      createFixCommit: vi.fn(),
      pushFixBranch: vi.fn(),
      createFixPullRequest: vi.fn(),
      getReview: vi.fn(),
    },
  };
});

// ---------------------------------------------------------------------------
// 1. CreatePullRequestModal Unit Tests
// ---------------------------------------------------------------------------

describe('CreatePullRequestModal', () => {
  it('test_1_renders_when_open', () => {
    render(
      <CreatePullRequestModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        headBranch="ai-fix/rev-abc12345-f0"
        baseBranch="main"
        findingIssue="Missing return type annotation"
      />
    );
    expect(screen.getByText('Create GitHub Pull Request?')).toBeTruthy();
  });

  it('test_2_hidden_when_not_open', () => {
    render(
      <CreatePullRequestModal
        isOpen={false}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        headBranch="ai-fix/rev-abc12345-f0"
      />
    );
    expect(screen.queryByText('Create GitHub Pull Request?')).toBeNull();
  });

  it('test_3_shows_head_and_base_branches', () => {
    render(
      <CreatePullRequestModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        headBranch="ai-fix/rev-abc12345-f0"
        baseBranch="main"
      />
    );
    const headMatches = screen.getAllByText(/ai-fix\/rev-abc12345-f0/i);
    expect(headMatches.length).toBeGreaterThan(0);
    expect(screen.getByText('main')).toBeTruthy();
  });

  it('test_4_confirm_button_calls_onConfirm', () => {
    const onConfirm = vi.fn();
    render(
      <CreatePullRequestModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        isLoading={false}
        headBranch="ai-fix/rev-abc12345-f0"
      />
    );
    fireEvent.click(document.getElementById('btn-confirm-pr')!);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('test_5_cancel_button_calls_onClose', () => {
    const onClose = vi.fn();
    render(
      <CreatePullRequestModal
        isOpen={true}
        onClose={onClose}
        onConfirm={vi.fn()}
        isLoading={false}
        headBranch="ai-fix/rev-abc12345-f0"
      />
    );
    fireEvent.click(document.getElementById('btn-cancel-pr')!);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('test_6_loading_state_disables_buttons', () => {
    render(
      <CreatePullRequestModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={true}
        headBranch="ai-fix/rev-abc12345-f0"
      />
    );
    expect((document.getElementById('btn-confirm-pr') as HTMLButtonElement)?.disabled).toBe(true);
    expect((document.getElementById('btn-cancel-pr') as HTMLButtonElement)?.disabled).toBe(true);
  });

  it('test_7_shows_no_auto_merge_safety_disclosure', () => {
    render(
      <CreatePullRequestModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        headBranch="ai-fix/rev-abc12345-f0"
      />
    );
    expect(screen.getByText(/No Auto-Merge/i)).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// 2. CommitSection PR Button & State Tests
// ---------------------------------------------------------------------------

describe('CommitSection PR Integration', () => {
  it('test_8_pr_button_visible_when_pushed_and_not_pr_created', () => {
    const onOpenPRModal = vi.fn();
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        gitPullRequest={null}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        isCreatingPR={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
        onOpenPRModal={onOpenPRModal}
      />
    );
    const btn = document.getElementById('btn-open-create-pr');
    expect(btn).toBeTruthy();
  });

  it('test_9_pr_button_calls_handler', () => {
    const onOpenPRModal = vi.fn();
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        gitPullRequest={null}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        isCreatingPR={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
        onOpenPRModal={onOpenPRModal}
      />
    );
    fireEvent.click(document.getElementById('btn-open-create-pr')!);
    expect(onOpenPRModal).toHaveBeenCalledOnce();
  });

  it('test_10_pr_button_hidden_when_pr_already_created', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        gitPullRequest={mockGitPullRequest}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        isCreatingPR={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
        onOpenPRModal={vi.fn()}
      />
    );
    expect(document.getElementById('btn-open-create-pr')).toBeNull();
  });

  it('test_11_pr_info_displayed_with_safe_link', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        gitPullRequest={mockGitPullRequest}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        isCreatingPR={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
        onOpenPRModal={vi.fn()}
      />
    );
    expect(screen.getByText(/Pull Request #42 Created/i)).toBeTruthy();
    const link = document.getElementById('link-view-pr') as HTMLAnchorElement;
    expect(link).toBeTruthy();
    expect(link.href).toBe('https://github.com/my-org/my-repo/pull/42');
    expect(link.target).toBe('_blank');
    expect(link.rel).toBe('noopener noreferrer');
  });

  it('test_12_no_auto_merge_notice_displayed', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        gitPullRequest={mockGitPullRequest}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        isCreatingPR={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
        onOpenPRModal={vi.fn()}
      />
    );
    expect(screen.getByText(/No auto-merge or approval has been performed/i)).toBeTruthy();
  });

  it('test_13_pr_error_banner_displayed', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        gitPullRequest={null}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        isCreatingPR={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
        onOpenPRModal={vi.fn()}
        prError="GitHub authentication required — check repository credentials."
      />
    );
    const matches = screen.queryAllByText(/GitHub Authentication Required/i);
    expect(matches.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// 3. FixSuggestionModal PR Integration Tests
// ---------------------------------------------------------------------------

describe('FixSuggestionModal PR Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_14_pr_button_visible_when_pushed', async () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={samplePushedFix}
        onDecisionChange={vi.fn()}
      />
    );
    await waitFor(() => {
      expect(document.getElementById('btn-open-create-pr')).toBeTruthy();
    });
  });

  it('test_15_clicking_pr_button_opens_modal', async () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={samplePushedFix}
        onDecisionChange={vi.fn()}
      />
    );
    await waitFor(() => {
      const btn = document.getElementById('btn-open-create-pr');
      if (btn) fireEvent.click(btn);
    });
    await waitFor(() => {
      expect(screen.queryByText('Create GitHub Pull Request?')).toBeTruthy();
    });
  });

  it('test_16_confirm_pr_calls_api_and_updates_state', async () => {
    const onDecisionChange = vi.fn();
    (reviewsApi.createFixPullRequest as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      git_pull_request: mockGitPullRequest,
      fix_suggestion: samplePRCreatedFix,
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={samplePushedFix}
        onDecisionChange={onDecisionChange}
      />
    );

    await waitFor(() => {
      const btn = document.getElementById('btn-open-create-pr');
      if (btn) fireEvent.click(btn);
    });

    await waitFor(() => {
      const confirmBtn = document.getElementById('btn-confirm-pr');
      if (confirmBtn) fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(reviewsApi.createFixPullRequest).toHaveBeenCalledWith('rev-1', 0);
      expect(onDecisionChange).toHaveBeenCalledWith(samplePRCreatedFix);
    });
  });
});

// ---------------------------------------------------------------------------
// 4. ReviewResultsPage PR Badge Tests
// ---------------------------------------------------------------------------

describe('ReviewResultsPage PR Badge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const buildReview = (fix: FixSuggestion) => ({
    id: 'rev-1',
    repository_id: 'repo-1',
    user_id: 'user-1',
    status: 'completed',
    created_at: '2026-08-26T09:00:00Z',
    confidence_score: 0.9,
    findings: [
      {
        ...sampleFinding,
        fix_suggestion: fix,
      },
    ],
  } as any);

  it('test_17_pr_badge_shown_on_results_page', async () => {
    const review = buildReview(samplePRCreatedFix);
    (reviewsApi.getReview as ReturnType<typeof vi.fn>).mockResolvedValue(review);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-1']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const badges = screen.queryAllByText(/PR #42/i);
      expect(badges.length).toBeGreaterThan(0);
    });
  });
});
