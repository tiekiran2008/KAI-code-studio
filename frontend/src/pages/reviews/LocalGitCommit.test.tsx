import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { FixSuggestionModal } from './FixSuggestionModal';
import { ReviewResultsPage } from './ReviewResultsPage';
import {
  reviewsApi,
  CodeReview,
  ReviewFinding,
  FixSuggestion,
  GitCommitResult,
} from '../../api/reviews';

const sampleFinding: ReviewFinding = {
  issue: 'Missing return type hint',
  severity: 'medium',
  explanation: 'Function is missing return type annotation.',
  suggested_fix: 'Add return type annotation -> int.',
  confidence_score: 0.95,
  file_path: 'src/calc.py',
  line_number: 10,
};

const sampleEligibleFix: FixSuggestion = {
  finding_index: 0,
  file_path: 'src/calc.py',
  original_code: 'def add(a, b):\n    return a + b',
  proposed_code: 'def add(a: int, b: int) -> int:\n    return a + b',
  explanation: 'Added type hints.',
  diff: '--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,2 +1,2 @@\n-def add(a, b):\n+def add(a: int, b: int) -> int:',
  confidence_score: 0.95,
  validation_status: 'valid',
  user_decision: 'accepted',
  application_status: 'applied',
  applied_at: '2026-08-26T09:00:00Z',
  static_verification: {
    status: 'passed',
    language: 'py',
    verified_at: '2026-08-26T09:05:00Z',
    verified_hash: 'abc1234567890abcdef',
    duration_ms: 15,
    checks: [],
    errors: [],
    warnings: [],
  },
};

const mockSuccessGitCommit: GitCommitResult = {
  status: 'committed',
  branch_name: 'ai-fix/rev-12345678-f0',
  commit_sha: 'a1b2c3d4e5f67890abcdef1234567890abcdef12',
  committed_at: '2026-08-26T09:10:00Z',
  file_path: 'src/calc.py',
  commit_message: 'fix: resolve finding 0 in src/calc.py',
  base_branch: 'main',
  base_commit_sha: '0000000000000000000000000000000000000000',
  message: 'Created commit a1b2c3d on branch ai-fix/rev-12345678-f0',
};

describe('Phase 11.5B-3 — Local Git Commit Frontend UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------------------------------------------------------------------------
  // 1. Eligibility & Ineligibility
  // ---------------------------------------------------------------------------

  it('1. Eligibility: Create Commit button is visible when fix is applied and static verification passed', () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(document.getElementById('btn-open-create-commit')).toBeInTheDocument();
  });

  it('2. Ineligible: Create Commit is not active when fix is not applied', () => {
    const unappliedFix: FixSuggestion = {
      ...sampleEligibleFix,
      application_status: 'not_applied',
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={unappliedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(document.getElementById('btn-open-create-commit')).not.toBeInTheDocument();
    expect(screen.getByText(/apply fix suggestion to enable local git commit/i)).toBeInTheDocument();
  });

  it('3. Ineligible: Create Commit is not active when static verification failed', () => {
    const failedVerifFix: FixSuggestion = {
      ...sampleEligibleFix,
      static_verification: {
        status: 'failed',
        errors: ['Syntax error'],
        warnings: [],
        checks: [],
      },
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={failedVerifFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(document.getElementById('btn-open-create-commit')).not.toBeInTheDocument();
    expect(screen.getByText(/tier-1 static verification must pass before committing/i)).toBeInTheDocument();
  });

  it('4. Ineligible: Create Commit is not active when fix is stale', () => {
    const staleFix: FixSuggestion = {
      ...sampleEligibleFix,
      application_status: 'stale',
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={staleFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(document.getElementById('btn-open-create-commit')).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // 2. Confirmation & Cancel Flow
  // ---------------------------------------------------------------------------

  it('5. Confirmation: Clicking Create Commit opens confirmation modal without calling API', () => {
    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit');

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    const commitBtn = document.getElementById('btn-open-create-commit')!;
    fireEvent.click(commitBtn);

    expect(screen.getByRole('heading', { name: /create local git commit\?/i })).toBeInTheDocument();
    expect(screen.getByText(/target file to commit/i)).toBeInTheDocument();
    expect(screen.getByText(/nothing is pushed to github or remote repositories/i)).toBeInTheDocument();
    expect(spyCreateCommit).toHaveBeenCalledTimes(0);
  });

  it('6. Cancel: Clicking Cancel closes confirmation modal with 0 API calls', () => {
    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit');

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    fireEvent.click(document.getElementById('btn-open-create-commit')!);
    const cancelBtn = document.getElementById('btn-cancel-commit')!;
    fireEvent.click(cancelBtn);

    expect(screen.queryByText(/create local git commit\?/i)).not.toBeInTheDocument();
    expect(spyCreateCommit).toHaveBeenCalledTimes(0);
  });

  // ---------------------------------------------------------------------------
  // 3. Confirm Commit & API Invariants
  // ---------------------------------------------------------------------------

  it('7. Confirm Commit: Calls reviewsApi.createFixCommit with reviewId and findingIndex', async () => {
    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit').mockResolvedValueOnce({
      git_commit: mockSuccessGitCommit,
      fix_suggestion: {
        ...sampleEligibleFix,
        git_commit: mockSuccessGitCommit,
      },
    });

    const onDecisionChange = vi.fn();

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={onDecisionChange}
      />
    );

    fireEvent.click(document.getElementById('btn-open-create-commit')!);
    const confirmBtn = document.getElementById('btn-confirm-commit')!;
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(spyCreateCommit).toHaveBeenCalledTimes(1);
      expect(spyCreateCommit).toHaveBeenCalledWith('rev-1', 0);
      expect(onDecisionChange).toHaveBeenCalledWith(
        expect.objectContaining({
          git_commit: expect.objectContaining({
            status: 'committed',
            commit_sha: mockSuccessGitCommit.commit_sha,
            branch_name: 'ai-fix/rev-12345678-f0',
          }),
        })
      );
    });
  });

  it('8. Duplicate Prevention: Rapid confirm clicks invoke API only once', async () => {
    let resolvePromise: any;
    const pendingPromise = new Promise<{ git_commit: GitCommitResult; fix_suggestion: FixSuggestion }>(
      (res) => {
        resolvePromise = res;
      }
    );

    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit').mockReturnValueOnce(pendingPromise);

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    fireEvent.click(document.getElementById('btn-open-create-commit')!);
    const confirmBtn = document.getElementById('btn-confirm-commit')!;

    // Double click rapidly
    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn);

    expect(spyCreateCommit).toHaveBeenCalledTimes(1);

    // Resolve
    resolvePromise({
      git_commit: mockSuccessGitCommit,
      fix_suggestion: { ...sampleEligibleFix, git_commit: mockSuccessGitCommit },
    });
  });

  // ---------------------------------------------------------------------------
  // 4. Success State Display
  // ---------------------------------------------------------------------------

  it('9. Success State: Displays Local Commit Created, branch name, short SHA, and no-push notice', () => {
    const committedFix: FixSuggestion = {
      ...sampleEligibleFix,
      git_commit: mockSuccessGitCommit,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={committedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText(/local commit created/i)).toBeInTheDocument();
    expect(screen.getByText('ai-fix/rev-12345678-f0')).toBeInTheDocument();
    // Short SHA (first 7 characters: a1b2c3d)
    expect(screen.getByText('a1b2c3d')).toBeInTheDocument();
    expect(screen.getByText(/created locally\. nothing has been pushed\./i)).toBeInTheDocument();

    // Must NOT claim push or PR
    expect(screen.queryByText(/pushed to github/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/pr created/i)).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // 5. Persisted State & Refresh
  // ---------------------------------------------------------------------------

  it('10. Persistence: Render review with persisted Git commit displays committed state without API call', () => {
    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit');

    const committedFix: FixSuggestion = {
      ...sampleEligibleFix,
      git_commit: mockSuccessGitCommit,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={committedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText(/local commit created/i)).toBeInTheDocument();
    expect(document.getElementById('btn-open-create-commit')).not.toBeInTheDocument();
    expect(spyCreateCommit).toHaveBeenCalledTimes(0);
  });

  // ---------------------------------------------------------------------------
  // 6. Error Handling
  // ---------------------------------------------------------------------------

  it('11. Stale Source Error: 409 stale source displays Source Changed Since Apply', async () => {
    vi.spyOn(reviewsApi, 'createFixCommit').mockRejectedValueOnce({
      status: 409,
      message: 'Source file was modified after fix was applied. Cannot commit stale source.',
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    fireEvent.click(document.getElementById('btn-open-create-commit')!);
    fireEvent.click(document.getElementById('btn-confirm-commit')!);

    await waitFor(() => {
      expect(screen.getByText(/source changed since apply/i)).toBeInTheDocument();
      expect(screen.queryByText(/local commit created/i)).not.toBeInTheDocument();
    });
  });

  it('12. Git Repository Required Error: Displays Git Repository Required without git-init button', async () => {
    vi.spyOn(reviewsApi, 'createFixCommit').mockRejectedValueOnce({
      status: 400,
      message: 'Workspace is not a valid Git repository',
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    fireEvent.click(document.getElementById('btn-open-create-commit')!);
    fireEvent.click(document.getElementById('btn-confirm-commit')!);

    await waitFor(() => {
      expect(screen.getByText(/git repository required/i)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /git init/i })).not.toBeInTheDocument();
    });
  });

  it('13. Generic Error: Displays Local Commit Failed without false success', async () => {
    vi.spyOn(reviewsApi, 'createFixCommit').mockRejectedValueOnce({
      status: 500,
      message: 'Internal error creating commit object',
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    fireEvent.click(document.getElementById('btn-open-create-commit')!);
    fireEvent.click(document.getElementById('btn-confirm-commit')!);

    await waitFor(() => {
      expect(screen.getByText(/local commit failed/i)).toBeInTheDocument();
      expect(screen.queryByText(/local commit created/i)).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // 7. No Automatic Commit Proofs
  // ---------------------------------------------------------------------------

  it('14. No Auto-Commit: Accepting a fix does NOT call createFixCommit', async () => {
    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit');
    vi.spyOn(reviewsApi, 'acceptFix').mockResolvedValueOnce({
      fix_suggestion: { ...sampleEligibleFix, user_decision: 'accepted' },
    });

    const pendingFix: FixSuggestion = {
      ...sampleEligibleFix,
      user_decision: 'pending',
      application_status: 'not_applied',
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={pendingFix}
        onDecisionChange={vi.fn()}
      />
    );

    const acceptBtn = document.getElementById('btn-accept-suggestion')!;
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(spyCreateCommit).toHaveBeenCalledTimes(0);
    });
  });

  it('15. No Auto-Commit: Applying a fix does NOT call createFixCommit', async () => {
    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit');
    vi.spyOn(reviewsApi, 'applyFix').mockResolvedValueOnce({
      fix_suggestion: { ...sampleEligibleFix, application_status: 'applied' },
      idempotent: false,
    });

    const unappliedFix: FixSuggestion = {
      ...sampleEligibleFix,
      application_status: 'not_applied',
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={unappliedFix}
        onDecisionChange={vi.fn()}
      />
    );

    const applyBtn = document.getElementById('btn-apply-suggestion')!;
    fireEvent.click(applyBtn);

    const confirmApplyBtn = document.getElementById('btn-confirm-apply')!;
    fireEvent.click(confirmApplyBtn);

    await waitFor(() => {
      expect(spyCreateCommit).toHaveBeenCalledTimes(0);
    });
  });

  it('16. No Auto-Commit: Static verification does NOT call createFixCommit', async () => {
    const spyCreateCommit = vi.spyOn(reviewsApi, 'createFixCommit');
    vi.spyOn(reviewsApi, 'verifyFix').mockResolvedValueOnce({
      verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      fix_suggestion: sampleEligibleFix,
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleEligibleFix}
        onDecisionChange={vi.fn()}
      />
    );

    const verifyBtn = document.getElementById('btn-verify-fix-modal')!;
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(spyCreateCommit).toHaveBeenCalledTimes(0);
    });
  });

  // ---------------------------------------------------------------------------
  // 8. Safe HTML Rendering
  // ---------------------------------------------------------------------------

  it('17. Safe Rendering: Branch name with special characters is rendered as plain text', () => {
    const xssBranchFix: FixSuggestion = {
      ...sampleEligibleFix,
      git_commit: {
        ...mockSuccessGitCommit,
        branch_name: '<script>alert(1)</script>',
      },
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={xssBranchFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('<script>alert(1)</script>')).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // 9. ReviewResultsPage Badge Integration
  // ---------------------------------------------------------------------------

  it('18. ReviewResultsPage: Displays Committed (local) badge for finding with local git commit', async () => {
    const mockReview: CodeReview = {
      id: 'rev-1',
      repository_id: 'repo-1',
      user_id: 'user-1',
      status: 'completed',
      created_at: '2026-08-26T08:00:00Z',
      findings: [
        {
          ...sampleFinding,
          fix_suggestion: {
            ...sampleEligibleFix,
            git_commit: mockSuccessGitCommit,
          },
        },
      ],
    } as any;

    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReview);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-1']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/committed \(local\)/i)).toBeInTheDocument();
    });
  });
});
