/**
 * Frontend Tests — Phase 11.5B-4 Push AI Fix Branch
 * ==================================================
 * Tests:
 * - PushBranchModal rendering, confirm/cancel actions, loading state
 * - CommitSection push button visibility, pushed state display, error display
 * - FixSuggestionModal integration (push button triggers modal, API call, state update)
 * - ReviewResultsPage "Pushed (origin)" badge visibility
 *
 * LLM calls: 0  shell: 0  force-push: 0  PR creation: 0
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { FixSuggestionModal } from './FixSuggestionModal';
import { ReviewResultsPage } from './ReviewResultsPage';
import { PushBranchModal } from './PushBranchModal';
import { CommitSection } from './CommitSection';
import {
  reviewsApi,
  ReviewFinding,
  FixSuggestion,
  GitCommitResult,
  GitPushResult,
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

const sampleAppliedFix: FixSuggestion = {
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
  remote_url_masked: 'https://github.com/user/repo.git',
  pushed_at: '2026-08-26T09:15:00Z',
  message: 'Pushed to origin',
};

const sampleCommittedFix: FixSuggestion = {
  ...sampleAppliedFix,
  git_commit: mockGitCommit,
};

const samplePushedFix: FixSuggestion = {
  ...sampleCommittedFix,
  git_push: mockGitPush,
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
      getReview: vi.fn(),
    },
  };
});

// ---------------------------------------------------------------------------
// 1. PushBranchModal Unit Tests
// ---------------------------------------------------------------------------

describe('PushBranchModal', () => {
  it('test_1_renders_when_open', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
        commitSha="a1b2c3d4e5f6"
      />
    );
    expect(screen.getByText('Push AI Fix Branch?')).toBeTruthy();
  });

  it('test_2_hidden_when_not_open', () => {
    render(
      <PushBranchModal
        isOpen={false}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    expect(screen.queryByText('Push AI Fix Branch?')).toBeNull();
  });

  it('test_3_shows_branch_name', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    const matches = screen.getAllByText(/ai-fix\/rev-abc12345-f0/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  it('test_4_shows_short_commit_sha', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
        commitSha="abcdef1234567890"
      />
    );
    expect(screen.getByText('abcdef1')).toBeTruthy();
  });

  it('test_5_confirm_button_calls_onConfirm', () => {
    const onConfirm = vi.fn();
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={onConfirm}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    fireEvent.click(screen.getByTestId ? screen.getByText('Push Branch') : document.getElementById('btn-confirm-push')!);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('test_6_cancel_button_calls_onClose', () => {
    const onClose = vi.fn();
    render(
      <PushBranchModal
        isOpen={true}
        onClose={onClose}
        onConfirm={vi.fn()}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    fireEvent.click(document.getElementById('btn-cancel-push')!);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('test_7_loading_state_disables_buttons', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={true}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    expect((document.getElementById('btn-confirm-push') as HTMLButtonElement)?.disabled).toBe(true);
    expect((document.getElementById('btn-cancel-push') as HTMLButtonElement)?.disabled).toBe(true);
  });

  it('test_8_loading_shows_pushing_text', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={true}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    expect(screen.getByText('Pushing branch...')).toBeTruthy();
  });

  it('test_9_no_force_push_in_modal_text', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    expect(screen.getByText(/No Force Push/i)).toBeTruthy();
  });

  it('test_10_no_pr_in_modal_text', () => {
    render(
      <PushBranchModal
        isOpen={true}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
        isLoading={false}
        branchName="ai-fix/rev-abc12345-f0"
      />
    );
    expect(screen.getByText(/No Pull Request/i)).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// 2. CommitSection Push Button Tests
// ---------------------------------------------------------------------------

describe('CommitSection Push Button', () => {
  it('test_11_push_button_visible_when_committed_not_pushed', () => {
    const onOpenPushModal = vi.fn();
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={null}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={onOpenPushModal}
      />
    );
    const btn = document.getElementById('btn-open-push-branch');
    expect(btn).toBeTruthy();
  });

  it('test_12_push_button_calls_handler', () => {
    const onOpenPushModal = vi.fn();
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={null}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={onOpenPushModal}
      />
    );
    fireEvent.click(document.getElementById('btn-open-push-branch')!);
    expect(onOpenPushModal).toHaveBeenCalledOnce();
  });

  it('test_13_push_button_hidden_when_already_pushed', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
      />
    );
    expect(document.getElementById('btn-open-push-branch')).toBeNull();
  });

  it('test_14_pushed_badge_shown_when_pushed', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
      />
    );
    expect(screen.getByText('Branch Pushed')).toBeTruthy();
  });

  it('test_15_pushed_notice_no_pr_message', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={mockGitPush}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
      />
    );
    expect(screen.getByText(/No Pull Request has been created yet/i)).toBeTruthy();
  });

  it('test_16_push_error_shown', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={null}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
        pushError="Authentication required — check credentials."
      />
    );
    const matches = screen.queryAllByText(/Authentication required/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  it('test_17_not_pushed_shows_nothing_pushed_notice', () => {
    render(
      <CommitSection
        gitCommit={mockGitCommit}
        gitPush={null}
        isApplied={true}
        staticPassed={true}
        isCommitting={false}
        isPushing={false}
        onOpenConfirmModal={vi.fn()}
        onOpenPushModal={vi.fn()}
      />
    );
    expect(screen.getByText(/Nothing has been pushed/i)).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// 3. FixSuggestionModal Integration Tests
// ---------------------------------------------------------------------------

describe('FixSuggestionModal Push Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_18_push_button_visible_when_fix_committed', async () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleCommittedFix}
        onDecisionChange={vi.fn()}
      />
    );
    await waitFor(() => {
      expect(document.getElementById('btn-open-push-branch')).toBeTruthy();
    });
  });

  it('test_19_push_button_not_visible_before_commit', async () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleAppliedFix}
        onDecisionChange={vi.fn()}
      />
    );
    await waitFor(() => {
      expect(document.getElementById('btn-open-push-branch')).toBeNull();
    });
  });

  it('test_20_push_modal_opens_on_button_click', async () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleCommittedFix}
        onDecisionChange={vi.fn()}
      />
    );
    await waitFor(() => {
      const pushBtn = document.getElementById('btn-open-push-branch');
      if (pushBtn) fireEvent.click(pushBtn);
    });
    await waitFor(() => {
      expect(screen.queryByText('Push AI Fix Branch?')).toBeTruthy();
    });
  });

  it('test_21_push_api_called_on_confirm', async () => {
    const onDecisionChange = vi.fn();
    (reviewsApi.pushFixBranch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      git_push: mockGitPush,
      fix_suggestion: samplePushedFix,
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleCommittedFix}
        onDecisionChange={onDecisionChange}
      />
    );

    // Open modal
    await waitFor(() => {
      const btn = document.getElementById('btn-open-push-branch');
      if (btn) fireEvent.click(btn);
    });

    // Confirm push
    await waitFor(() => {
      const confirmBtn = document.getElementById('btn-confirm-push');
      if (confirmBtn) fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(reviewsApi.pushFixBranch).toHaveBeenCalledWith('rev-1', 0);
    });
  });

  it('test_22_push_success_calls_onDecisionChange', async () => {
    const onDecisionChange = vi.fn();
    (reviewsApi.pushFixBranch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      git_push: mockGitPush,
      fix_suggestion: samplePushedFix,
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleCommittedFix}
        onDecisionChange={onDecisionChange}
      />
    );

    await waitFor(() => {
      const btn = document.getElementById('btn-open-push-branch');
      if (btn) fireEvent.click(btn);
    });

    await waitFor(() => {
      const confirmBtn = document.getElementById('btn-confirm-push');
      if (confirmBtn) fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(onDecisionChange).toHaveBeenCalledWith(samplePushedFix);
    });
  });
});

// ---------------------------------------------------------------------------
// 4. ReviewResultsPage Push Badge Tests
// ---------------------------------------------------------------------------

describe('ReviewResultsPage Push Badge', () => {
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

  it('test_23_pushed_badge_shown_on_results_page', async () => {
    const review = buildReview(samplePushedFix);
    (reviewsApi.getReview as ReturnType<typeof vi.fn>).mockResolvedValue(review);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-1']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const badges = screen.queryAllByText(/Pushed \(origin\)/i);
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it('test_24_pushed_badge_not_shown_when_only_committed', async () => {
    const review = buildReview(sampleCommittedFix);
    (reviewsApi.getReview as ReturnType<typeof vi.fn>).mockResolvedValue(review);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-1']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const badges = screen.queryAllByText(/Pushed \(origin\)/i);
      expect(badges.length).toBe(0);
    });
  });
});
