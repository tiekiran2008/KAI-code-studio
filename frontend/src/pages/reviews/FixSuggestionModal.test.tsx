import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import React from 'react';
import { FixSuggestionModal } from './FixSuggestionModal';
import { ReviewFinding, FixSuggestion, reviewsApi } from '../../api/reviews';

const sampleFinding: ReviewFinding = {
  issue: 'Unused variable temp',
  severity: 'medium',
  explanation: 'Variable temp is initialized but never read or modified.',
  suggested_fix: 'Remove variable temp.',
  confidence_score: 0.92,
  file_path: 'src/calculator.py',
  line_number: 10,
};

const sampleFix: FixSuggestion = {
  finding_index: 0,
  file_path: 'src/calculator.py',
  original_code: 'def add(a, b):\n    temp = 1\n    return a + b',
  proposed_code: 'def add(a, b):\n    return a + b',
  explanation: 'Removed unused variable temp to improve code cleanliness.',
  diff: '--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -1,3 +1,2 @@\n def add(a, b):\n-    temp = 1\n     return a + b',
  confidence_score: 0.95,
  validation_status: 'valid',
  user_decision: 'pending',
  language: 'py',
  validation_message: 'Python syntax verified',
};

describe('FixSuggestionModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders issue title, file path, validation status, and confidence score', () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Unused variable temp')).toBeInTheDocument();
    expect(screen.getByText('src/calculator.py:10')).toBeInTheDocument();
    expect(screen.getByText('Valid Syntax')).toBeInTheDocument();
    expect(screen.getByText('95% Confidence')).toBeInTheDocument();
    expect(screen.getByText(/Removed unused variable temp/i)).toBeInTheDocument();
  });

  it('displays unified diff with color-coded additions and deletions as plain text', () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText(/--- a\/src\/calculator\.py/)).toBeInTheDocument();
    expect(screen.getByText(/\+\+\+ b\/src\/calculator\.py/)).toBeInTheDocument();
    expect(screen.getByText(/-.*temp = 1/)).toBeInTheDocument();
    expect(screen.getByText(/return a \+ b/)).toBeInTheDocument();
  });

  it('switches between Unified Diff, Side-by-Side, Proposed Code, and Original Code views', () => {
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={vi.fn()}
      />
    );

    // Switch to Proposed Code view
    const proposedTab = screen.getByRole('button', { name: /Proposed Code/i });
    fireEvent.click(proposedTab);
    expect(screen.getByText('Proposed Fixed Snippet')).toBeInTheDocument();

    // Switch to Original Code view
    const originalTab = screen.getByRole('button', { name: /Original Code/i });
    fireEvent.click(originalTab);
    expect(screen.getByText('Original Source Snippet')).toBeInTheDocument();

    // Switch back to Unified Diff
    const diffTab = screen.getByRole('button', { name: /Unified Diff/i });
    fireEvent.click(diffTab);
    expect(screen.getByText(/--- a\/src\/calculator\.py/)).toBeInTheDocument();
  });

  it('calls acceptFix and triggers onDecisionChange when Accept Suggestion is clicked', async () => {
    const mockOnDecisionChange = vi.fn();
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };
    vi.spyOn(reviewsApi, 'acceptFix').mockResolvedValueOnce({ fix_suggestion: acceptedFix });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={mockOnDecisionChange}
      />
    );

    const acceptBtn = screen.getByRole('button', { name: /Accept Suggestion/i });
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(reviewsApi.acceptFix).toHaveBeenCalledWith('rev-123', 0);
      expect(mockOnDecisionChange).toHaveBeenCalledWith(acceptedFix);
    });
  });

  it('calls rejectFix and triggers onDecisionChange when Reject Suggestion is clicked', async () => {
    const mockOnDecisionChange = vi.fn();
    const rejectedFix: FixSuggestion = { ...sampleFix, user_decision: 'rejected' };
    vi.spyOn(reviewsApi, 'rejectFix').mockResolvedValueOnce({ fix_suggestion: rejectedFix });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={mockOnDecisionChange}
      />
    );

    const rejectBtn = screen.getByRole('button', { name: /Reject Suggestion/i });
    fireEvent.click(rejectBtn);

    await waitFor(() => {
      expect(reviewsApi.rejectFix).toHaveBeenCalledWith('rev-123', 0);
      expect(mockOnDecisionChange).toHaveBeenCalledWith(rejectedFix);
    });
  });

  it('displays Accepted Suggestion status when user_decision is accepted', () => {
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={acceptedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getAllByText('Accepted Suggestion').length).toBeGreaterThanOrEqual(1);
  });

  it('displays Rejected Suggestion status when user_decision is rejected', () => {
    const rejectedFix: FixSuggestion = { ...sampleFix, user_decision: 'rejected' };
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={rejectedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getAllByText('Rejected Suggestion').length).toBeGreaterThanOrEqual(1);
  });

  it('calls onClose when close button is clicked', () => {
    const mockOnClose = vi.fn();
    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={mockOnClose}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={vi.fn()}
      />
    );

    const closeBtn = screen.getByLabelText(/Close modal/i);
    fireEvent.click(closeBtn);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('shows error banner when acceptFix fails without crashing modal', async () => {
    vi.spyOn(reviewsApi, 'acceptFix').mockRejectedValueOnce(new Error('Network failure'));

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={vi.fn()}
      />
    );

    const acceptBtn = screen.getByRole('button', { name: /Accept Suggestion/i });
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(screen.getByText('Network failure')).toBeInTheDocument();
    });
  });

  // ─── Phase 11.3B-4 Apply Suggestion & Explicit Confirmation Tests ────────────

  it('27. Accept separation: clicking Accept Suggestion calls acceptFix and does NOT call applyFix', async () => {
    const applySpy = vi.spyOn(reviewsApi, 'applyFix');
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };
    vi.spyOn(reviewsApi, 'acceptFix').mockResolvedValueOnce({ fix_suggestion: acceptedFix });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={sampleFix}
        onDecisionChange={vi.fn()}
      />
    );

    const acceptBtn = screen.getByRole('button', { name: /Accept Suggestion/i });
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(reviewsApi.acceptFix).toHaveBeenCalledWith('rev-123', 0);
      expect(applySpy).not.toHaveBeenCalled();
    });
  });

  it('28. Confirmation flow: clicking Apply Suggestion opens confirmation modal without calling applyFix; Cancel closes it without API calls', async () => {
    const applySpy = vi.spyOn(reviewsApi, 'applyFix');
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={acceptedFix}
        onDecisionChange={vi.fn()}
      />
    );

    const applyBtn = screen.getByRole('button', { name: /Apply Suggestion/i });
    fireEvent.click(applyBtn);

    // Confirmation modal should be visible with explicit warning and file path
    expect(screen.getByText('Apply Fix to Local File')).toBeInTheDocument();
    expect(screen.getByText('Explicit Confirmation Required')).toBeInTheDocument();
    expect(screen.getByText('src/calculator.py')).toBeInTheDocument();
    expect(applySpy).not.toHaveBeenCalled();

    // Click Cancel
    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    // Modal closed, 0 API calls
    expect(screen.queryByText('Explicit Confirmation Required')).not.toBeInTheDocument();
    expect(applySpy).not.toHaveBeenCalled();
  });

  it('29. Apply success: confirming Apply Fix calls applyFix exactly once and renders Applied state', async () => {
    const mockOnDecisionChange = vi.fn();
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };
    const appliedFix: FixSuggestion = {
      ...acceptedFix,
      application_status: 'applied',
      applied_at: '2026-08-25T09:00:00Z',
    };
    vi.spyOn(reviewsApi, 'applyFix').mockResolvedValueOnce({
      fix_suggestion: appliedFix,
      idempotent: false,
    });

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={acceptedFix}
        onDecisionChange={mockOnDecisionChange}
      />
    );

    // Open confirmation
    fireEvent.click(screen.getByRole('button', { name: /Apply Suggestion/i }));

    // Confirm Apply
    const confirmBtn = screen.getByRole('button', { name: /Apply Fix/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(reviewsApi.applyFix).toHaveBeenCalledTimes(1);
      expect(reviewsApi.applyFix).toHaveBeenCalledWith('rev-123', 0);
      expect(mockOnDecisionChange).toHaveBeenCalledWith(appliedFix);
    });
  });

  it('30. Double click protection: rapid clicks on Confirm Apply trigger only one request while pending', async () => {
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };
    const appliedFix: FixSuggestion = { ...acceptedFix, application_status: 'applied' };

    let resolveApply: (value: any) => void;
    const applyPromise = new Promise((resolve) => {
      resolveApply = resolve;
    });
    vi.spyOn(reviewsApi, 'applyFix').mockImplementationOnce(() => applyPromise as any);

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={acceptedFix}
        onDecisionChange={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Apply Suggestion/i }));

    const confirmBtn = screen.getByRole('button', { name: /Apply Fix/i });
    // First click
    fireEvent.click(confirmBtn);
    // Rapid second and third clicks
    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn);

    expect(reviewsApi.applyFix).toHaveBeenCalledTimes(1);

    // Resolve promise
    await act(async () => {
      resolveApply!({ fix_suggestion: appliedFix, idempotent: false });
    });
  });

  it('31. Stale source UX: 409 / stale error shows clear warning and updates status to Stale without false success', async () => {
    const mockOnDecisionChange = vi.fn();
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };
    const staleError = new Error('Stale source detected: file content changed');
    (staleError as any).status = 409;
    vi.spyOn(reviewsApi, 'applyFix').mockRejectedValueOnce(staleError);

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={acceptedFix}
        onDecisionChange={mockOnDecisionChange}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Apply Suggestion/i }));
    fireEvent.click(screen.getByRole('button', { name: /Apply Fix/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Source changed after this suggestion was generated/i)
      ).toBeInTheDocument();
      expect(mockOnDecisionChange).toHaveBeenCalledWith(
        expect.objectContaining({ application_status: 'stale' })
      );
    });
  });

  it('32. Failure UX: generic backend error displays Apply Failed without false success', async () => {
    const mockOnDecisionChange = vi.fn();
    const acceptedFix: FixSuggestion = { ...sampleFix, user_decision: 'accepted' };
    vi.spyOn(reviewsApi, 'applyFix').mockRejectedValueOnce(new Error('Internal server error'));

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={acceptedFix}
        onDecisionChange={mockOnDecisionChange}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Apply Suggestion/i }));
    fireEvent.click(screen.getByRole('button', { name: /Apply Fix/i }));

    await waitFor(() => {
      expect(screen.getByText('Internal server error')).toBeInTheDocument();
      expect(mockOnDecisionChange).toHaveBeenCalledWith(
        expect.objectContaining({ application_status: 'apply_failed' })
      );
    });
  });

  it('33. Already applied state: renders Applied to File badge and disabled Applied button with no active Apply button', () => {
    const appliedFix: FixSuggestion = {
      ...sampleFix,
      user_decision: 'accepted',
      application_status: 'applied',
      applied_at: '2026-08-25T09:00:00Z',
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={appliedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.getByText('Applied to File')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Applied/i })).toBeDisabled();
    expect(screen.queryByRole('button', { name: /Apply Suggestion/i })).not.toBeInTheDocument();
  });

  it('35. Rejected state: Apply Suggestion button is unavailable', () => {
    const rejectedFix: FixSuggestion = { ...sampleFix, user_decision: 'rejected' };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={rejectedFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: /Apply Suggestion/i })).not.toBeInTheDocument();
  });

  it('36. Invalid validation status: Apply Suggestion button is unavailable', () => {
    const invalidFix: FixSuggestion = {
      ...sampleFix,
      user_decision: 'accepted',
      validation_status: 'invalid',
    };

    render(
      <FixSuggestionModal
        isOpen={true}
        onClose={vi.fn()}
        reviewId="rev-123"
        findingIndex={0}
        finding={sampleFinding}
        fixSuggestion={invalidFix}
        onDecisionChange={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: /Apply Suggestion/i })).not.toBeInTheDocument();
  });
});

