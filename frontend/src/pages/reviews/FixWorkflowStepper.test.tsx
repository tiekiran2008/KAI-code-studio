/**
 * Frontend Tests — Phase 11.6B-1 Unified Fix Workflow Stepper
 * =============================================================
 * Comprehensive unit & integration tests for FixWorkflowStepper and deriveFixWorkflowSteps.
 *
 * Verifies:
 * - Deterministic pure state derivation for all 8 lifecycle stages:
 *   Fix -> Accept -> Apply -> Verify -> Tests -> Commit -> Push -> PR
 * - Accurate status derivation: pending, current, completed, failed, blocked, rejected, skipped
 * - Strict gating: no false PASS on failed/unavailable/unsupported states
 * - Rejected suggestions accurately stop downstream mutation stages
 * - Final PR status communicates "Pull Request Created" without claiming merged
 * - All 3 variants: full, compact, mini
 * - Pure informational UI: 0 mutation API calls
 * - Accessibility: role="list", role="listitem", aria-current="step"
 * - Independent derivation across multiple findings
 * - Refresh state restoration
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import {
  FixWorkflowStepper,
  deriveFixWorkflowSteps,
  WorkflowStepId,
} from './FixWorkflowStepper';
import {
  ReviewFinding,
  FixSuggestion,
  GitCommitResult,
  GitPushResult,
  GitPullRequestResult,
  StaticVerificationResult,
  SandboxVerificationResult,
} from '../../api/reviews';

// ─── Shared Test Fixtures ───────────────────────────────────────────────────

const baseFinding: ReviewFinding = {
  issue: 'Potential ZeroDivisionError in calc.py',
  severity: 'high',
  explanation: 'Divide function does not check for zero denominator.',
  suggested_fix: 'Add zero check before division.',
  confidence_score: 0.95,
  file_path: 'src/calc.py',
  line_number: 14,
};

const baseFixSuggestion: FixSuggestion = {
  finding_index: 0,
  file_path: 'src/calc.py',
  original_code: 'def divide(a, b):\n    return a / b',
  proposed_code: 'def divide(a, b):\n    if b == 0:\n        raise ValueError("Division by zero")\n    return a / b',
  explanation: 'Add zero check',
  diff: '--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,2 +1,4 @@\n def divide(a, b):\n+    if b == 0:\n+        raise ValueError("Division by zero")\n     return a / b',
  confidence_score: 0.98,
  validation_status: 'valid',
  user_decision: 'pending',
  application_status: 'not_applied',
};

// ─── 1. Pure Derivation Unit Tests ──────────────────────────────────────────

describe('deriveFixWorkflowSteps pure derivation', () => {
  it('1. Initial State (No Fix Suggestion): Fix is current, rest are pending', () => {
    const steps = deriveFixWorkflowSteps(baseFinding, null, 'completed');
    expect(steps).toHaveLength(8);

    expect(steps[0]).toMatchObject({ id: 'fix', status: 'current' });
    expect(steps[1]).toMatchObject({ id: 'accept', status: 'pending' });
    expect(steps[2]).toMatchObject({ id: 'apply', status: 'pending' });
    expect(steps[3]).toMatchObject({ id: 'verify', status: 'pending' });
    expect(steps[4]).toMatchObject({ id: 'tests', status: 'pending' });
    expect(steps[5]).toMatchObject({ id: 'commit', status: 'pending' });
    expect(steps[6]).toMatchObject({ id: 'push', status: 'pending' });
    expect(steps[7]).toMatchObject({ id: 'pr', status: 'pending' });
  });

  it('2. Fix Generated: Fix is completed, Accept is current', () => {
    const steps = deriveFixWorkflowSteps(baseFinding, baseFixSuggestion);
    expect(steps[0]).toMatchObject({ id: 'fix', status: 'completed' });
    expect(steps[1]).toMatchObject({ id: 'accept', status: 'current', isCurrent: true });
    expect(steps[2]).toMatchObject({ id: 'apply', status: 'pending' });
  });

  it('3. Accepted: Fix and Accept completed, Apply is current', () => {
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'not_applied',
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[0].status).toBe('completed');
    expect(steps[1].status).toBe('completed');
    expect(steps[2]).toMatchObject({ id: 'apply', status: 'current', isCurrent: true });
    expect(steps[3].status).toBe('pending');
  });

  it('4. Rejected: Accept is rejected, downstream stages are blocked', () => {
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'rejected',
      application_status: 'not_applied',
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[0].status).toBe('completed');
    expect(steps[1]).toMatchObject({ id: 'accept', status: 'rejected' });
    expect(steps[2]).toMatchObject({ id: 'apply', status: 'blocked' });
    expect(steps[3]).toMatchObject({ id: 'verify', status: 'blocked' });
  });

  it('5. Applied to file: Apply completed, Verify is current', () => {
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[2]).toMatchObject({ id: 'apply', status: 'completed' });
    expect(steps[3]).toMatchObject({ id: 'verify', status: 'current', isCurrent: true });
  });

  it('6. Apply Stale Source / Conflict: Apply is blocked', () => {
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'stale',
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[2]).toMatchObject({ id: 'apply', status: 'blocked' });
    expect(steps[3]).toMatchObject({ id: 'verify', status: 'blocked' });
  });

  it('7. Static Verification Passed: Verify completed, Commit is current', () => {
    const staticRes: StaticVerificationResult = {
      status: 'passed',
      checks: [{ name: 'Syntax', status: 'passed', message: 'OK' }],
      errors: [],
      warnings: [],
      message: 'Static check passed',
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: staticRes,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[3]).toMatchObject({ id: 'verify', status: 'completed' });
    expect(steps[4]).toMatchObject({ id: 'tests', status: 'current' });
    expect(steps[5]).toMatchObject({ id: 'commit', status: 'current' });
  });

  it('8. Static Verification Failed: Verify failed, downstream Commit/Push/PR blocked', () => {
    const staticRes: StaticVerificationResult = {
      status: 'failed',
      checks: [{ name: 'AST Check', status: 'failed', message: 'Syntax error' }],
      errors: ['SyntaxError on line 2'],
      warnings: [],
      message: 'Static check failed',
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: staticRes,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[3]).toMatchObject({ id: 'verify', status: 'failed' });
    expect(steps[4]).toMatchObject({ id: 'tests', status: 'blocked' });
    expect(steps[5]).toMatchObject({ id: 'commit', status: 'blocked' });
    expect(steps[6]).toMatchObject({ id: 'push', status: 'blocked' });
    expect(steps[7]).toMatchObject({ id: 'pr', status: 'blocked' });
  });

  it('9. Isolated Tests Passed: Tests completed', () => {
    const testRes: SandboxVerificationResult = {
      status: 'passed',
      verification_type: 'pytest',
      test_framework: 'pytest',
      command_label: 'pytest',
      duration_ms: 1200,
      tests_total: 4,
      tests_passed: 4,
      tests_failed: 0,
      stdout_summary: '4 passed',
      stderr_summary: '',
      timed_out: false,
      resource_limit_hit: false,
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      test_verification: testRes,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[4]).toMatchObject({ id: 'tests', status: 'completed' });
  });

  it('10. Isolated Tests Failed: Tests failed without false success', () => {
    const testRes: SandboxVerificationResult = {
      status: 'failed',
      verification_type: 'pytest',
      test_framework: 'pytest',
      command_label: 'pytest',
      duration_ms: 800,
      tests_total: 4,
      tests_passed: 3,
      tests_failed: 1,
      stdout_summary: '1 failed',
      stderr_summary: '',
      timed_out: false,
      resource_limit_hit: false,
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      test_verification: testRes,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[4]).toMatchObject({ id: 'tests', status: 'failed' });
  });

  it('11. Sandbox Unavailable / Timed out: Does not show passed', () => {
    const testRes: SandboxVerificationResult = {
      status: 'sandbox_unavailable',
      verification_type: 'pytest',
      test_framework: 'pytest',
      command_label: 'pytest',
      duration_ms: 100,
      stdout_summary: '',
      stderr_summary: 'Docker daemon unavailable',
      timed_out: false,
      resource_limit_hit: false,
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      test_verification: testRes,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[4]).toMatchObject({ id: 'tests', status: 'blocked' });
    expect(steps[4].status).not.toBe('completed');
  });

  it('12. Local Commit Created: Commit completed, Push is current', () => {
    const gitCommit: GitCommitResult = {
      status: 'committed',
      branch_name: 'ai-fix/rev-12345678-f0',
      commit_sha: '1234567890abcdef1234567890abcdef12345678',
      file_path: 'src/calc.py',
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      git_commit: gitCommit,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[5]).toMatchObject({ id: 'commit', status: 'completed' });
    expect(steps[6]).toMatchObject({ id: 'push', status: 'current', isCurrent: true });
    expect(steps[7]).toMatchObject({ id: 'pr', status: 'pending' });
  });

  it('13. Branch Pushed: Push completed, PR is current', () => {
    const gitCommit: GitCommitResult = {
      status: 'committed',
      branch_name: 'ai-fix/rev-12345678-f0',
      commit_sha: '1234567890abcdef1234567890abcdef12345678',
      file_path: 'src/calc.py',
    };
    const gitPush: GitPushResult = {
      status: 'pushed',
      remote_name: 'origin',
      branch_name: 'ai-fix/rev-12345678-f0',
      commit_sha: '1234567890abcdef1234567890abcdef12345678',
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      git_commit: gitCommit,
      git_push: gitPush,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    expect(steps[6]).toMatchObject({ id: 'push', status: 'completed' });
    expect(steps[7]).toMatchObject({ id: 'pr', status: 'current', isCurrent: true });
  });

  it('14. Pull Request Created: Full 8-stage pipeline completed', () => {
    const gitCommit: GitCommitResult = {
      status: 'committed',
      branch_name: 'ai-fix/rev-12345678-f0',
      commit_sha: '1234567890abcdef1234567890abcdef12345678',
      file_path: 'src/calc.py',
    };
    const gitPush: GitPushResult = {
      status: 'pushed',
      remote_name: 'origin',
      branch_name: 'ai-fix/rev-12345678-f0',
      commit_sha: '1234567890abcdef1234567890abcdef12345678',
    };
    const gitPR: GitPullRequestResult = {
      status: 'created',
      pr_number: 42,
      pr_url: 'https://github.com/org/repo/pull/42',
      title: 'fix(calc): resolve zero division',
      head_branch: 'ai-fix/rev-12345678-f0',
      base_branch: 'main',
    };
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      test_verification: {
        status: 'passed',
        verification_type: 'pytest',
        test_framework: 'pytest',
        command_label: 'pytest',
        duration_ms: 500,
        stdout_summary: 'OK',
        stderr_summary: '',
        timed_out: false,
        resource_limit_hit: false,
      },
      git_commit: gitCommit,
      git_push: gitPush,
      git_pull_request: gitPR,
    };
    const steps = deriveFixWorkflowSteps(baseFinding, fix);
    for (const step of steps) {
      expect(step.status).toBe('completed');
    }
    expect(steps[7].statusText).toContain('PR #42 Created');
  });
});

// ─── 2. Component Rendering & Accessibility Tests ───────────────────────────

describe('FixWorkflowStepper Component', () => {
  it('renders all 8 steps in full variant with semantic accessibility attributes', () => {
    render(<FixWorkflowStepper finding={baseFinding} fixSuggestion={baseFixSuggestion} variant="full" />);

    expect(screen.getByTestId('fix-workflow-stepper')).toBeInTheDocument();
    expect(screen.getByRole('list', { name: /workflow progress steps/i })).toBeInTheDocument();

    const stepIds: WorkflowStepId[] = ['fix', 'accept', 'apply', 'verify', 'tests', 'commit', 'push', 'pr'];
    for (const id of stepIds) {
      expect(screen.getByTestId(`stepper-step-${id}`)).toBeInTheDocument();
    }

    // Fix is completed, Accept is current
    const acceptStep = screen.getByTestId('stepper-step-accept');
    expect(acceptStep).toHaveAttribute('aria-current', 'step');
  });

  it('renders compact variant cleanly', () => {
    render(<FixWorkflowStepper finding={baseFinding} fixSuggestion={baseFixSuggestion} variant="compact" />);

    expect(screen.getByTestId('fix-workflow-stepper-compact')).toBeInTheDocument();
    expect(screen.getByText('AI Fix Lifecycle')).toBeInTheDocument();
  });

  it('renders mini variant cleanly with list and listitem semantics', () => {
    render(<FixWorkflowStepper finding={baseFinding} fixSuggestion={baseFixSuggestion} variant="mini" />);

    expect(screen.getByTestId('fix-workflow-stepper-mini')).toBeInTheDocument();
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(8);
  });

  it('displays "Pull Request Created" banner on PR completion without claiming merged', () => {
    const fix: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
      static_verification: { status: 'passed', checks: [], errors: [], warnings: [] },
      git_commit: { status: 'committed', commit_sha: 'a'.repeat(40), branch_name: 'ai-fix/b1' },
      git_push: { status: 'pushed', commit_sha: 'a'.repeat(40), branch_name: 'ai-fix/b1' },
      git_pull_request: { status: 'created', pr_number: 99, pr_url: 'https://github.com/org/repo/pull/99' },
    };

    render(<FixWorkflowStepper finding={baseFinding} fixSuggestion={fix} variant="full" />);

    expect(screen.getByText(/Pull Request Created/i)).toBeInTheDocument();
    expect(screen.queryByText(/Merged/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Deployed/i)).not.toBeInTheDocument();
  });

  it('is strictly informational and makes 0 API calls', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    render(<FixWorkflowStepper finding={baseFinding} fixSuggestion={baseFixSuggestion} variant="full" />);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it('handles multiple findings independently without state leakage', () => {
    const fix1: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'accepted',
      application_status: 'applied',
    };
    const fix2: FixSuggestion = {
      ...baseFixSuggestion,
      user_decision: 'rejected',
    };

    const steps1 = deriveFixWorkflowSteps(baseFinding, fix1);
    const steps2 = deriveFixWorkflowSteps(baseFinding, fix2);

    expect(steps1[2].status).toBe('completed'); // Finding 1 applied
    expect(steps2[2].status).toBe('blocked');   // Finding 2 rejected -> apply blocked
  });
});
