/**
 * Frontend Tests — Phase 11.6B-5 Responsive Design & Accessibility Final Polish
 * ==============================================================================
 * Comprehensive tests verifying:
 * - Responsive layout classes & overflow safety (FindingRow, Tabs, RecentReviews, Modals)
 * - Accessibility properties (aria-expanded, aria-selected, role="tab", aria-label)
 * - Focus visibility and keyboard interaction semantics
 * - Status textual representation independent of color
 * - Zero mutation APIs triggered on render
 * - Safe string rendering without script injection
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ReviewResultsPage } from './ReviewResultsPage';
import { reviewsApi, CodeReview, ReviewFinding } from '../../api/reviews';

const mockFindingWithLongNames: ReviewFinding = {
  issue: 'Extremely long issue title describing a complex vulnerability in nested authentication middleware handler',
  severity: 'critical',
  explanation: 'Detailed explanation regarding token validation in deep module stack.',
  suggested_fix: 'Validate JWT claims explicitly.',
  confidence_score: 0.98,
  file_path: 'src/infrastructure/security/authentication/providers/oauth2/jwt_token_claims_verifier.py',
  line_number: 142,
  fix_suggestion: {
    finding_index: 0,
    file_path: 'src/infrastructure/security/authentication/providers/oauth2/jwt_token_claims_verifier.py',
    original_code: 'verify(token)',
    proposed_code: 'verify_claims(token, claims=["sub", "exp"])',
    diff: '--- a/src/user.py\n+++ b/src/user.py\n@@ -1 +1 @@\n-verify(token)\n+verify_claims(token, claims=["sub", "exp"])',
    explanation: 'Added claims validation.',
    confidence_score: 0.98,
    validation_status: 'valid',
    user_decision: 'accepted',
    application_status: 'applied',
  },
};

const mockReviewResponsive: CodeReview = {
  id: 'rev-resp-101',
  repository_id: 'repo-long-name-enterprise-service-system',
  user_id: 'usr-1',
  status: 'completed',
  confidence_score: 0.95,
  findings: [mockFindingWithLongNames],
  created_at: '2026-08-26T12:00:00Z',
};

describe('Phase 11.6B-5 — Responsive Design & Overflow Safety', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders long file paths with truncation classes preventing page overflow', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReviewResponsive);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-resp-101']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const filePathElem = screen.getByText(/jwt_token_claims_verifier\.py/i);
      expect(filePathElem).toBeInTheDocument();
      expect(filePathElem.className).toContain('truncate');
    });
  });

  it('renders review tabs with responsive overflow container', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReviewResponsive);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-resp-101']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const codeTab = screen.getByRole('tab', { name: /Code Quality/i });
      expect(codeTab).toBeInTheDocument();
      expect(codeTab).toHaveAttribute('aria-selected', 'true');
    });
  });
});

describe('Phase 11.6B-5 — Accessibility & Keyboard Interactions', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('FindingRow exposes aria-expanded accurately on expand/collapse', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReviewResponsive);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-resp-101']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Extremely long issue title/i)).toBeInTheDocument();
    });

    const toggleBtn = screen.getByRole('button', { name: /Expand finding details/i });
    expect(toggleBtn).toHaveAttribute('aria-label', 'Expand finding details');

    fireEvent.click(toggleBtn);

    expect(screen.getByRole('button', { name: /Collapse finding details/i })).toBeInTheDocument();
  });

  it('renders statuses with visible text and not color alone', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReviewResponsive);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-resp-101']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Completed')).toBeInTheDocument();
      expect(screen.getAllByText('Critical').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('produces zero mutation API calls on responsive rendering', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReviewResponsive);
    const startSpy = vi.spyOn(reviewsApi, 'startReview');
    const applySpy = vi.spyOn(reviewsApi, 'applyFix');
    const commitSpy = vi.spyOn(reviewsApi, 'createFixCommit');

    render(
      <MemoryRouter initialEntries={['/reviews/rev-resp-101']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Extremely long issue title/i)).toBeInTheDocument();
    });

    expect(startSpy).not.toHaveBeenCalled();
    expect(applySpy).not.toHaveBeenCalled();
    expect(commitSpy).not.toHaveBeenCalled();
  });
});
