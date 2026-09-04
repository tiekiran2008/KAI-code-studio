import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { FixSuggestionModal } from './FixSuggestionModal';
import { ReviewResultsPage } from './ReviewResultsPage';
import {
  reviewsApi,
  CodeReview,
  ReviewFinding,
  FixSuggestion,
  StaticVerificationResult,
} from '../../api/reviews';

const sampleFinding: ReviewFinding = {
  issue: 'Syntax error in math utility',
  severity: 'high',
  explanation: 'Missing closing parenthesis in calculation function.',
  suggested_fix: 'Add closing parenthesis.',
  confidence_score: 0.95,
  file_path: 'src/math_utils.py',
  line_number: 14,
};

const sampleAppliedFix: FixSuggestion = {
  finding_index: 0,
  file_path: 'src/math_utils.py',
  original_code: 'def calc(a, b):\n    return (a + b',
  proposed_code: 'def calc(a, b):\n    return (a + b)',
  explanation: 'Added closing parenthesis.',
  diff: '--- a/src/math_utils.py\n+++ b/src/math_utils.py\n@@ -1,2 +1,2 @@\n def calc(a, b):\n-    return (a + b\n+    return (a + b)',
  confidence_score: 0.95,
  validation_status: 'valid',
  user_decision: 'accepted',
  application_status: 'applied',
  applied_at: '2026-08-26T09:00:00Z',
};

const mockPassedVerification: StaticVerificationResult = {
  status: 'passed',
  language: 'py',
  verified_at: '2026-08-26T09:05:00Z',
  verified_hash: 'abc1234567890abcdef',
  duration_ms: 15,
  checks: [
    {
      name: 'python_ast_parse',
      status: 'passed',
      message: 'Python AST parsed successfully with 0 errors.',
    },
    {
      name: 'conflict_marker_check',
      status: 'passed',
      message: 'No git conflict markers found in source.',
    },
    {
      name: 'source_hash_integrity',
      status: 'passed',
      message: 'Current file content hash matches applied fix hash.',
    },
  ],
  errors: [],
  warnings: [],
  message: 'Static verification passed for python_ast_parse',
};

const mockFailedVerification: StaticVerificationResult = {
  status: 'failed',
  language: 'py',
  verified_at: '2026-08-26T09:06:00Z',
  verified_hash: 'def9876543210fedcba',
  duration_ms: 22,
  checks: [
    {
      name: 'python_ast_parse',
      status: 'failed',
      message: 'SyntaxError: unexpected EOF while parsing',
      line_number: 14,
      column: 18,
    },
    {
      name: 'conflict_marker_check',
      status: 'passed',
      message: 'No conflict markers found.',
    },
  ],
  errors: ['SyntaxError: unexpected EOF while parsing (line 14, col 18)'],
  warnings: [],
  message: 'Static verification failed: SyntaxError',
};

const mockUnsupportedVerification: StaticVerificationResult = {
  status: 'unsupported',
  language: 'clojure',
  verified_at: '2026-08-26T09:07:00Z',
  duration_ms: 5,
  checks: [
    {
      name: 'language_support_check',
      status: 'unsupported',
      message: 'Language "clojure" is not supported for in-memory AST verification.',
    },
  ],
  errors: [],
  warnings: ['Language parser not available.'],
  message: 'Static verification not supported for clojure',
};

const mockSourceChangedVerification: StaticVerificationResult = {
  status: 'source_changed',
  language: 'py',
  verified_at: '2026-08-26T09:08:00Z',
  duration_ms: 10,
  checks: [
    {
      name: 'source_hash_integrity',
      status: 'failed',
      message: 'Current file hash does not match the post-apply hash.',
    },
  ],
  errors: ['Source changed after apply. Hash mismatch detected.'],
  warnings: [],
  message: 'Source changed after apply',
};

describe('Phase 11.4B-3 — Static Verification Frontend UI & Status UX', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── 1. ELIGIBILITY ──────────────────────────────────────────────────────────
  it('24. Eligibility: Verify Fix button is visible for applied fixes and hidden for not_applied, stale, and apply_failed', () => {
    // Applied fix -> Verify Fix visible
    const { unmount: unmount1 } = render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleAppliedFix}
        onDecisionChange={vi.fn()}
      />
    );
    expect(screen.getAllByRole('button', { name: /Verify Fix/i }).length).toBeGreaterThanOrEqual(1);
    unmount1();

    // Not applied fix -> Verify Fix not visible
    const notAppliedFix: FixSuggestion = {
      ...sampleAppliedFix,
      application_status: 'not_applied',
    };
    const { unmount: unmount2 } = render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={notAppliedFix}
        onDecisionChange={vi.fn()}
      />
    );
    expect(screen.queryByRole('button', { name: /Verify Fix/i })).not.toBeInTheDocument();
    unmount2();

    // Stale fix -> Verify Fix not visible
    const staleFix: FixSuggestion = {
      ...sampleAppliedFix,
      application_status: 'stale',
    };
    const { unmount: unmount3 } = render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={staleFix}
        onDecisionChange={vi.fn()}
      />
    );
    expect(screen.queryByRole('button', { name: /Verify Fix/i })).not.toBeInTheDocument();
    unmount3();

    // Apply failed fix -> Verify Fix not visible
    const failedFix: FixSuggestion = {
      ...sampleAppliedFix,
      application_status: 'apply_failed',
    };
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={failedFix}
        onDecisionChange={vi.fn()}
      />
    );
    expect(screen.queryByRole('button', { name: /Verify Fix/i })).not.toBeInTheDocument();
  });

  // ─── 2. VERIFY REQUEST & SECURITY ────────────────────────────────────────────
  it('25. Verify Action: clicking Verify Fix calls reviewsApi.verifyFix(reviewId, findingIndex) with no extra body parameters', async () => {
    const verifySpy = vi.spyOn(reviewsApi, 'verifyFix').mockResolvedValueOnce({
      verification: mockPassedVerification,
      fix_suggestion: {
        ...sampleAppliedFix,
        static_verification: mockPassedVerification,
      },
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleAppliedFix}
        onDecisionChange={vi.fn()}
      />
    );

    const verifyBtn = screen.getAllByRole('button', { name: /Verify Fix/i })[0];
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(verifySpy).toHaveBeenCalledTimes(1);
      expect(verifySpy).toHaveBeenCalledWith('rev-100', 0);
    });
  });

  // ─── 3. LOADING STATE & DUPLICATE PROTECTION ─────────────────────────────────
  it('26. Loading State: shows Verifying state and prevents duplicate requests while in-flight', async () => {
    let resolveVerify: (val: any) => void;
    const verifyPromise = new Promise((resolve) => {
      resolveVerify = resolve;
    });
    const verifySpy = vi.spyOn(reviewsApi, 'verifyFix').mockImplementationOnce(() => verifyPromise as any);

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleAppliedFix}
        onDecisionChange={vi.fn()}
      />
    );

    const verifyBtn = screen.getAllByRole('button', { name: /Verify Fix/i })[0];
    fireEvent.click(verifyBtn);

    // Should show Verifying loading text
    expect(screen.getAllByText(/Verifying\.\.\./i).length).toBeGreaterThanOrEqual(1);

    // Rapid double-clicks should be ignored
    fireEvent.click(verifyBtn);
    fireEvent.click(verifyBtn);
    expect(verifySpy).toHaveBeenCalledTimes(1);

    // Resolve
    await act(async () => {
      resolveVerify!({
        verification: mockPassedVerification,
        fix_suggestion: {
          ...sampleAppliedFix,
          static_verification: mockPassedVerification,
        },
      });
    });
  });

  // ─── 4. PASSED UX & CRITICAL LANGUAGE RULE ───────────────────────────────────
  it('27. Passed UX: displays "Static Verification Passed" and NEVER displays "Tests Passed"', () => {
    const verifiedFix: FixSuggestion = {
      ...sampleAppliedFix,
      static_verification: mockPassedVerification,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={verifiedFix}
        onDecisionChange={vi.fn()}
      />
    );

    // Clear static verification pass text
    expect(screen.getAllByText(/Static Verification Passed/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Configured static and syntax checks passed.')).toBeInTheDocument();
    expect(screen.getByText('python_ast_parse')).toBeInTheDocument();
    expect(screen.getByText('conflict_marker_check')).toBeInTheDocument();

    // CRITICAL LANGUAGE RULE ASSERTION:
    const bodyText = document.body.textContent || '';
    expect(bodyText).not.toMatch(/Tests Passed/i);
    expect(bodyText).not.toMatch(/Runtime verified/i);
    expect(bodyText).not.toMatch(/Production ready/i);
  });

  // ─── 5. FAILED UX ────────────────────────────────────────────────────────────
  it('28. Failed UX: renders "Static Verification Failed", structured checks, errors, and line/column numbers', () => {
    const failedFix: FixSuggestion = {
      ...sampleAppliedFix,
      static_verification: mockFailedVerification,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={failedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getAllByText(/Static Verification Failed/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/SyntaxError: unexpected EOF/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Line 14:18')).toBeInTheDocument();
  });

  // ─── 6. UNSUPPORTED UX ───────────────────────────────────────────────────────
  it('29. Unsupported UX: displays "Static Verification Not Supported for This Language" without false success', () => {
    const unsupportedFix: FixSuggestion = {
      ...sampleAppliedFix,
      static_verification: mockUnsupportedVerification,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={unsupportedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(
      screen.getAllByText(/Verification Unsupported|Static Verification Not Supported for This Language/i).length
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText(/Static syntax verification parser is not available for this language/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Static Verification Passed/i)).not.toBeInTheDocument();
  });

  // ─── 7. SOURCE CHANGED UX ────────────────────────────────────────────────────
  it('30. Source Changed UX: displays "Source Changed After Apply" warning and no false PASS', () => {
    const sourceChangedFix: FixSuggestion = {
      ...sampleAppliedFix,
      static_verification: mockSourceChangedVerification,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sourceChangedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getAllByText(/Source Changed After Apply/i).length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText(/The current file no longer matches the version that was applied/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Static Verification Passed/i)).not.toBeInTheDocument();
  });

  // ─── 8. PERSISTENCE ──────────────────────────────────────────────────────────
  it('31. Persistence: renders review with existing verification result immediately without calling verify API on mount', async () => {
    const verifySpy = vi.spyOn(reviewsApi, 'verifyFix');
    const mockReview: CodeReview = {
      id: 'rev-test-200',
      repository_id: 'repo-abc',
      user_id: 'user-xyz',
      status: 'completed',
      confidence_score: 0.95,
      created_at: '2026-08-26T09:00:00Z',
      findings: [
        {
          ...sampleFinding,
          fix_suggestion: {
            ...sampleAppliedFix,
            static_verification: mockPassedVerification,
          },
        },
      ],
    };
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReview);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-test-200/results']}>
        <Routes>
          <Route path="/reviews/:reviewId/results" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Syntax error in math utility')).toBeInTheDocument();
    });

    // Badge indicates Static Verified immediately
    expect(screen.getByText('Static Verified')).toBeInTheDocument();
    // Zero automated verifyFix API calls on mount
    expect(verifySpy).not.toHaveBeenCalled();
  });

  // ─── 9. RE-VERIFY ────────────────────────────────────────────────────────────
  it('32. Re-verify: clicking Re-run Static Verification calls verifyFix and updates state', async () => {
    const mockOnDecisionChange = vi.fn();
    const verifiedFix: FixSuggestion = {
      ...sampleAppliedFix,
      static_verification: mockFailedVerification,
    };

    const reVerifiedFix: FixSuggestion = {
      ...sampleAppliedFix,
      static_verification: mockPassedVerification,
    };

    vi.spyOn(reviewsApi, 'verifyFix').mockResolvedValueOnce({
      verification: mockPassedVerification,
      fix_suggestion: reVerifiedFix,
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={verifiedFix}
        onDecisionChange={mockOnDecisionChange}
      />
    );

    const reRunBtn = screen.getAllByRole('button', { name: /Re-run Static Verification/i })[0];
    fireEvent.click(reRunBtn);

    await waitFor(() => {
      expect(reviewsApi.verifyFix).toHaveBeenCalledWith('rev-100', 0);
      expect(mockOnDecisionChange).toHaveBeenCalledWith(reVerifiedFix);
    });
  });

  // ─── 10. MULTIPLE FINDINGS INDEPENDENCE ──────────────────────────────────────
  it('33. Multiple Findings: verifying finding 0 does not alter finding 1 state', async () => {
    const finding1: ReviewFinding = {
      issue: 'Unused import sys',
      severity: 'low',
      explanation: 'sys is imported but unused.',
      confidence_score: 0.9,
      file_path: 'src/helpers.py',
      line_number: 1,
      fix_suggestion: {
        finding_index: 1,
        file_path: 'src/helpers.py',
        original_code: 'import sys',
        proposed_code: '',
        explanation: 'Removed import sys.',
        diff: '--- a/src/helpers.py\n+++ b/src/helpers.py\n@@ -1 +0,0 @@\n-import sys',
        confidence_score: 0.9,
        validation_status: 'valid',
        user_decision: 'accepted',
        application_status: 'applied',
        applied_at: '2026-08-26T09:00:00Z',
      },
    };

    const mockReview: CodeReview = {
      id: 'rev-multi-300',
      repository_id: 'repo-abc',
      user_id: 'user-xyz',
      status: 'completed',
      confidence_score: 0.95,
      created_at: '2026-08-26T09:00:00Z',
      findings: [
        {
          ...sampleFinding,
          fix_suggestion: {
            ...sampleAppliedFix,
            static_verification: null,
          },
        },
        finding1,
      ],
    };

    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReview);
    vi.spyOn(reviewsApi, 'verifyFix').mockResolvedValueOnce({
      verification: mockPassedVerification,
      fix_suggestion: {
        ...sampleAppliedFix,
        static_verification: mockPassedVerification,
      },
    });

    render(
      <MemoryRouter initialEntries={['/reviews/rev-multi-300/results']}>
        <Routes>
          <Route path="/reviews/:reviewId/results" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Syntax error in math utility')).toBeInTheDocument();
      expect(screen.getByText('Unused import sys')).toBeInTheDocument();
    });

    // Open finding 0 modal
    const viewButtons = screen.getAllByRole('button', { name: /View Fix/i });
    fireEvent.click(viewButtons[0]);

    // Click Verify Fix inside modal
    const verifyBtn = screen.getAllByRole('button', { name: /Verify Fix/i })[0];
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(reviewsApi.verifyFix).toHaveBeenCalledWith('rev-multi-300', 0);
    });

    // Close modal
    fireEvent.click(screen.getByLabelText(/Close modal/i));

    // Finding 0 should now show Static Verified
    expect(screen.getByText('Static Verified')).toBeInTheDocument();
    // Finding 1 should show Applied (without Static Verified badge)
    expect(screen.getAllByText('Applied').length).toBeGreaterThanOrEqual(1);
  });

  // ─── 11. ERROR HANDLING ──────────────────────────────────────────────────────
  it('34. Error Handling: API failure displays safe error message without fake verification result', async () => {
    vi.spyOn(reviewsApi, 'verifyFix').mockRejectedValueOnce(new Error('Internal verification server timeout'));

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-100"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleAppliedFix}
        onDecisionChange={vi.fn()}
      />
    );

    const verifyBtn = screen.getAllByRole('button', { name: /Verify Fix/i })[0];
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText('Internal verification server timeout')).toBeInTheDocument();
      expect(screen.queryByText(/Static Verification Passed/i)).not.toBeInTheDocument();
    });
  });
});
