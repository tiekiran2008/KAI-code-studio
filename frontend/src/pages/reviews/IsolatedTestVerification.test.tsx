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
  SandboxVerificationResult,
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

const mockPassedSandboxResult: SandboxVerificationResult = {
  status: 'passed',
  verification_type: 'isolated_tests',
  test_framework: 'pytest',
  command_label: 'pytest',
  exit_code: 0,
  duration_ms: 320,
  tests_total: 4,
  tests_passed: 4,
  tests_failed: 0,
  tests_skipped: 0,
  stdout_summary: 'test_calc.py .... [100%]\n4 passed in 0.32s',
  stderr_summary: '',
  timed_out: false,
  resource_limit_hit: false,
  verified_at: '2026-08-26T09:10:00Z',
  verified_hash: 'abc1234567890abcdef',
};

const mockFailedSandboxResult: SandboxVerificationResult = {
  status: 'failed',
  verification_type: 'isolated_tests',
  test_framework: 'pytest',
  command_label: 'pytest',
  exit_code: 1,
  duration_ms: 450,
  tests_total: 4,
  tests_passed: 3,
  tests_failed: 1,
  tests_skipped: 0,
  stdout_summary: 'test_calc.py ...F [100%]\nFAILED test_calc.py::test_edge_case\n3 passed, 1 failed in 0.45s',
  stderr_summary: 'AssertionError: assert False',
  timed_out: false,
  resource_limit_hit: false,
  verified_at: '2026-08-26T09:11:00Z',
  verified_hash: 'abc1234567890abcdef',
};

const mockTimedOutSandboxResult: SandboxVerificationResult = {
  status: 'timed_out',
  verification_type: 'isolated_tests',
  test_framework: 'pytest',
  command_label: 'pytest',
  exit_code: -1,
  duration_ms: 30000,
  tests_total: null,
  tests_passed: null,
  tests_failed: null,
  tests_skipped: null,
  stdout_summary: '',
  stderr_summary: 'Execution timed out after 30 seconds.',
  timed_out: true,
  resource_limit_hit: false,
  verified_at: '2026-08-26T09:12:00Z',
  verified_hash: 'abc1234567890abcdef',
};

const mockUnavailableSandboxResult: SandboxVerificationResult = {
  status: 'sandbox_unavailable',
  verification_type: 'isolated_tests',
  test_framework: 'pytest',
  command_label: 'pytest',
  exit_code: null,
  duration_ms: 0,
  tests_total: null,
  tests_passed: null,
  tests_failed: null,
  tests_skipped: null,
  stdout_summary: '',
  stderr_summary: '',
  timed_out: false,
  resource_limit_hit: false,
  message: 'Docker daemon is not available',
};

const mockUnsupportedSandboxResult: SandboxVerificationResult = {
  status: 'unsupported',
  verification_type: 'isolated_tests',
  test_framework: 'unsupported',
  command_label: 'N/A',
  exit_code: null,
  duration_ms: 0,
  tests_total: null,
  tests_passed: null,
  tests_failed: null,
  tests_skipped: null,
  stdout_summary: '',
  stderr_summary: '',
  timed_out: false,
  resource_limit_hit: false,
  message: 'Tier-2 container testing is only supported for Python/pytest projects',
};

const mockSourceChangedSandboxResult: SandboxVerificationResult = {
  status: 'source_changed',
  verification_type: 'isolated_tests',
  test_framework: 'pytest',
  command_label: 'pytest',
  exit_code: null,
  duration_ms: 0,
  tests_total: null,
  tests_passed: null,
  tests_failed: null,
  tests_skipped: null,
  stdout_summary: '',
  stderr_summary: '',
  timed_out: false,
  resource_limit_hit: false,
  message: 'Source file was modified after fix was applied',
};

describe('Phase 11.4B-7 Tier-2 Isolated Container Test Verification UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('29. Eligibility: Run Isolated Tests visible only when applied + static verification passed', () => {
    const onDecisionChange = vi.fn();
    const { rerender } = render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleAppliedFix}
        onDecisionChange={onDecisionChange}
      />
    );

    // Visible when applied + static passed
    expect(screen.getByText(/Run Isolated Tests/i)).toBeDefined();

    // Hidden when static verification failed
    const fixStaticFailed: FixSuggestion = {
      ...sampleAppliedFix,
      static_verification: { status: 'failed', checks: [], errors: [], warnings: [] },
    };
    rerender(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixStaticFailed}
        onDecisionChange={onDecisionChange}
      />
    );
    expect(screen.queryByRole('button', { name: /Run Isolated Tests/i })).toBeNull();
    expect(screen.getByText(/Tier-1 Static Verification must pass before isolated tests can be executed/i)).toBeDefined();

    // Hidden when not applied
    const fixNotApplied: FixSuggestion = {
      ...sampleAppliedFix,
      application_status: 'not_applied',
    };
    rerender(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixNotApplied}
        onDecisionChange={onDecisionChange}
      />
    );
    expect(screen.queryByRole('button', { name: /Run Isolated Tests/i })).toBeNull();
  });

  it('30. Confirmation: Clicking Run Isolated Tests opens dialog; Cancel makes 0 API calls', async () => {
    const verifySpy = vi.spyOn(reviewsApi, 'verifyFixTests');
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

    const runBtn = screen.getByRole('button', { name: /Run Isolated Tests/i });
    fireEvent.click(runBtn);

    // Confirmation dialog appears
    expect(screen.getByRole('dialog', { name: /Run Isolated Tests Confirmation/i })).toBeDefined();
    expect(screen.getByText(/Network Disabled/i)).toBeDefined();
    expect(screen.getByText(/Ephemeral Copy Protected/i)).toBeDefined();
    expect(verifySpy).not.toHaveBeenCalled();

    // Click Cancel
    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    // Dialog closes, 0 API calls
    expect(screen.queryByRole('dialog', { name: /Run Isolated Tests Confirmation/i })).toBeNull();
    expect(verifySpy).not.toHaveBeenCalled();
  });

  it('31. Run: Confirming Run Tests calls verifyFixTests(reviewId, findingIndex) exactly once', async () => {
    const updatedFix: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockPassedSandboxResult,
    };
    vi.spyOn(reviewsApi, 'verifyFixTests').mockResolvedValueOnce({
      verification: mockPassedSandboxResult,
      fix_suggestion: updatedFix,
    });
    const onDecisionChange = vi.fn();

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleAppliedFix}
        onDecisionChange={onDecisionChange}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Run Isolated Tests/i }));
    const confirmBtn = screen.getByRole('button', { name: /Run Tests/i });

    await act(async () => {
      fireEvent.click(confirmBtn);
    });

    expect(reviewsApi.verifyFixTests).toHaveBeenCalledTimes(1);
    expect(reviewsApi.verifyFixTests).toHaveBeenCalledWith('rev-1', 0);
    expect(onDecisionChange).toHaveBeenCalledWith(updatedFix);
  });

  it('32. Duplicate: Rapid clicks trigger only one active request', async () => {
    let resolvePromise: (val: any) => void = () => {};
    const pendingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    vi.spyOn(reviewsApi, 'verifyFixTests').mockReturnValue(pendingPromise as any);

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

    fireEvent.click(screen.getByRole('button', { name: /Run Isolated Tests/i }));
    const confirmBtn = screen.getByRole('button', { name: /Run Tests/i });

    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn);

    expect(reviewsApi.verifyFixTests).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolvePromise({
        verification: mockPassedSandboxResult,
        fix_suggestion: sampleAppliedFix,
      });
    });
  });

  it('33. Pass UX: Mock PASSED displays Isolated Tests Passed with accurate sandbox notice', () => {
    const fixWithPass: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockPassedSandboxResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixWithPass}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Isolated Tests Passed')).toBeDefined();
    expect(
      screen.getByText(/Allowed pytest checks completed successfully inside the isolated sandbox/i)
    ).toBeDefined();
    expect(screen.getByText(/Tests: 4 Total/i)).toBeDefined();
    expect(screen.getByText(/• 4 Passed/i)).toBeDefined();
    expect(screen.getByText(/320ms/i)).toBeDefined();
  });

  it('34. Fail UX: Mock FAILED displays Isolated Tests Failed with metrics and bounded output', () => {
    const fixWithFail: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockFailedSandboxResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixWithFail}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Isolated Tests Failed')).toBeDefined();
    expect(screen.getByText(/• 3 Passed/i)).toBeDefined();
    expect(screen.getByText(/• 1 Failed/i)).toBeDefined();
    expect(screen.getByText(/Exit Code:/i)).toBeDefined();
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/FAILED test_calc.py::test_edge_case/i)).toBeDefined();
    expect(screen.getByText(/AssertionError: assert False/i)).toBeDefined();
  });

  it('35. Timeout UX: Mock TIMED_OUT displays Test Execution Timed Out', () => {
    const fixWithTimeout: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockTimedOutSandboxResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixWithTimeout}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Test Execution Timed Out')).toBeDefined();
    expect(
      screen.getByText(
        /The sandbox stopped the test execution because the configured execution time limit was exceeded/i
      )
    ).toBeDefined();
    expect(screen.getByText(/Execution timed out after 30 seconds/i)).toBeDefined();
  });

  it('36. Sandbox Unavailable UX: Displays Sandbox Unavailable with zero host fallback', () => {
    const fixWithUnavailable: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockUnavailableSandboxResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixWithUnavailable}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Sandbox Unavailable')).toBeDefined();
    expect(
      screen.getByText('Isolated test execution is currently unavailable.')
    ).toBeDefined();
    // Ensure no prompt to run locally
    expect(screen.queryByText(/Run locally instead/i)).toBeNull();
  });

  it('37. Unsupported UX: Mock UNSUPPORTED is not styled or labeled as pass', () => {
    const fixWithUnsupported: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockUnsupportedSandboxResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixWithUnsupported}
        onDecisionChange={vi.fn()}
      />
    );

    expect(
      screen.getByText('Isolated Tests Not Supported for This Project')
    ).toBeDefined();
    expect(screen.queryByText('Isolated Tests Passed')).toBeNull();
  });

  it('38. Source Changed UX: Mock SOURCE_CHANGED displays safe status without tests passed', () => {
    const fixWithSourceChanged: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockSourceChangedSandboxResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixWithSourceChanged}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Source Changed Since Apply')).toBeDefined();
    expect(
      screen.getByText(/Source code was modified after fix application/i)
    ).toBeDefined();
    expect(screen.queryByText('Isolated Tests Passed')).toBeNull();
  });

  it('39. Persistence: Render persisted test_verification visible immediately with zero API calls', () => {
    const verifySpy = vi.spyOn(reviewsApi, 'verifyFixTests');
    const fixPersisted: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockPassedSandboxResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixPersisted}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Isolated Tests Passed')).toBeDefined();
    expect(verifySpy).not.toHaveBeenCalled();
  });

  it('40. Re-run: Explicit re-run button triggers confirmation and one new request', async () => {
    const fixPersisted: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: mockPassedSandboxResult,
    };
    vi.spyOn(reviewsApi, 'verifyFixTests').mockResolvedValueOnce({
      verification: mockPassedSandboxResult,
      fix_suggestion: fixPersisted,
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixPersisted}
        onDecisionChange={vi.fn()}
      />
    );

    const rerunBtn = screen.getByRole('button', { name: /Re-run Isolated Tests/i });
    fireEvent.click(rerunBtn);

    const confirmBtn = screen.getByRole('button', { name: /Run Tests/i });
    await act(async () => {
      fireEvent.click(confirmBtn);
    });

    expect(reviewsApi.verifyFixTests).toHaveBeenCalledTimes(1);
  });

  it('41. Multiple findings independence: testing finding 0 does not alter finding 1 state', async () => {
    const finding0Fix: FixSuggestion = {
      ...sampleAppliedFix,
      finding_index: 0,
      test_verification: mockPassedSandboxResult,
    };
    const finding1Fix: FixSuggestion = {
      ...sampleAppliedFix,
      finding_index: 1,
      test_verification: null,
    };

    const mockReview: CodeReview = {
      id: 'rev-multi',
      repository_id: 'repo-1',
      user_id: 'user-1',
      status: 'completed',
      findings: [
        { ...sampleFinding, fix_suggestion: finding0Fix },
        { ...sampleFinding, issue: 'Unused import', fix_suggestion: finding1Fix },
      ],
      confidence_score: 0.95,
      progress_percent: 100,
      created_at: '2026-08-26T08:00:00Z',
    };

    vi.spyOn(reviewsApi, 'getReview').mockResolvedValue(mockReview);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-multi/results']}>
        <Routes>
          <Route path="/reviews/:reviewId/results" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Syntax error in math utility')).toBeDefined();
    });

    // Finding 0 should have "Tests Passed" badge
    expect(screen.getByText('Tests Passed')).toBeDefined();

    // Finding 1 should NOT have "Tests Passed" badge
    const badges = screen.getAllByText(/Tests Passed/i);
    expect(badges.length).toBe(1);
  });

  it('42. Safe plain text output: XSS injection script renders purely as text without execution', () => {
    const maliciousResult: SandboxVerificationResult = {
      status: 'failed',
      verification_type: 'isolated_tests',
      test_framework: 'pytest',
      command_label: 'pytest',
      exit_code: 1,
      duration_ms: 100,
      stdout_summary: '<script>alert("xss")</script>',
      stderr_summary: '<img src=x onerror=alert(1)>',
      timed_out: false,
      resource_limit_hit: false,
    };

    const fixMalicious: FixSuggestion = {
      ...sampleAppliedFix,
      test_verification: maliciousResult,
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-1"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={fixMalicious}
        onDecisionChange={vi.fn()}
      />
    );

    // Text is rendered safely inside <pre> elements
    expect(screen.getByText('<script>alert("xss")</script>')).toBeDefined();
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeDefined();
  });
});
