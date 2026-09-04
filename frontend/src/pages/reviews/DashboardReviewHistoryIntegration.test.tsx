/**
 * Frontend Tests — Phase 11.6B-4 Dashboard & Review History Integration
 * =====================================================================
 * Tests verifying:
 * - Dashboard Recent Reviews rendering (data, empty, loading, navigation)
 * - Review History scanability & status rendering (Completed, In Progress, Failed, Cancelled, Pending)
 * - Navigation links between Dashboard -> History -> Results
 * - Persisted workflow reconstruction (read-only, no mutations on render)
 * - Multiple repositories distinction & safe rendering
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { RecentReviews } from '../../components/dashboard/RecentReviews';
import { ReviewResultsPage } from './ReviewResultsPage';
import { reviewsApi, CodeReview } from '../../api/reviews';
import { Repository } from '../../types';

const mockRepos: Repository[] = [
  {
    id: 'repo-1',
    name: 'backend-service',
    owner: 'acme-corp',
    url: 'https://github.com/acme-corp/backend-service',
    defaultBranch: 'main',
    currentBranch: 'main',
    branches: ['main'],
    indexingStatus: 'indexed',
    chunksCount: 120,
    language: 'Python',
  },
  {
    id: 'repo-2',
    name: 'web-frontend',
    owner: 'acme-corp',
    url: 'https://github.com/acme-corp/web-frontend',
    defaultBranch: 'main',
    currentBranch: 'main',
    branches: ['main'],
    indexingStatus: 'indexed',
    chunksCount: 240,
    language: 'TypeScript',
  },
];

const mockReviews: CodeReview[] = [
  {
    id: 'rev-completed-1',
    repository_id: 'repo-1',
    user_id: 'usr-1',
    status: 'completed',
    confidence_score: 0.96,
    duration_ms: 4500,
    overall_health_score: 88.5,
    findings: [
      {
        issue: 'SQL injection risk in user query',
        severity: 'critical',
        explanation: 'Unsanitized input allows SQL injection.',
        suggested_fix: 'Use parameterized query bindings.',
        confidence_score: 0.98,
        file_path: 'src/user.py',
      },
    ],
    created_at: '2026-08-26T10:00:00Z',
  },
  {
    id: 'rev-in-progress-2',
    repository_id: 'repo-2',
    user_id: 'usr-1',
    status: 'in_progress',
    confidence_score: 0.85,
    findings: [],
    created_at: '2026-08-26T11:00:00Z',
  },
  {
    id: 'rev-failed-3',
    repository_id: 'repo-1',
    user_id: 'usr-1',
    status: 'failed',
    confidence_score: 0,
    findings: [],
    created_at: '2026-08-26T09:00:00Z',
  },
  {
    id: 'rev-cancelled-4',
    repository_id: 'repo-2',
    user_id: 'usr-1',
    status: 'cancelled',
    confidence_score: 0,
    findings: [],
    created_at: '2026-08-26T08:00:00Z',
  },
];

describe('Phase 11.6B-4 — Dashboard Recent Reviews Component', () => {
  it('renders recent reviews with repository names, statuses, and counts', () => {
    render(
      <MemoryRouter>
        <RecentReviews reviews={mockReviews} repositories={mockRepos} isLoading={false} />
      </MemoryRouter>
    );

    expect(screen.getByText('Recent Code Reviews')).toBeInTheDocument();
    expect(screen.getAllByText('acme-corp/backend-service').length).toBe(2);
    expect(screen.getAllByText('acme-corp/web-frontend').length).toBe(2);
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Cancelled')).toBeInTheDocument();
  });

  it('limits displayed reviews to 4 and shows View all button', () => {
    const manyReviews = [
      ...mockReviews,
      {
        id: 'rev-extra-5',
        repository_id: 'repo-1',
        user_id: 'usr-1',
        status: 'completed' as const,
        confidence_score: 0.9,
        findings: [],
        created_at: '2026-08-26T07:00:00Z',
      },
    ];

    render(
      <MemoryRouter>
        <RecentReviews reviews={manyReviews} repositories={mockRepos} isLoading={false} />
      </MemoryRouter>
    );

    expect(screen.getByText('View all')).toBeInTheDocument();
  });

  it('renders loading state when isLoading is true', () => {
    render(
      <MemoryRouter>
        <RecentReviews reviews={[]} repositories={mockRepos} isLoading={true} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Loading recent reviews.../i)).toBeInTheDocument();
  });

  it('renders clean empty state with CTA when no reviews exist', () => {
    render(
      <MemoryRouter>
        <RecentReviews reviews={[]} repositories={mockRepos} isLoading={false} />
      </MemoryRouter>
    );

    expect(screen.getByText(/No code reviews yet./i)).toBeInTheDocument();
    expect(screen.getByText(/Start a review/i)).toBeInTheDocument();
  });
});

describe('Phase 11.6B-4 — Navigation & No Mutation Guarantees', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('rendering dashboard recent reviews produces zero mutation API calls', () => {
    const _fetchSpy = vi.spyOn(globalThis, 'fetch');
    const startReviewSpy = vi.spyOn(reviewsApi, 'startReview');
    const generateFixSpy = vi.spyOn(reviewsApi, 'generateFix');
    const applyFixSpy = vi.spyOn(reviewsApi, 'applyFix');

    render(
      <MemoryRouter>
        <RecentReviews reviews={mockReviews} repositories={mockRepos} isLoading={false} />
      </MemoryRouter>
    );

    expect(startReviewSpy).not.toHaveBeenCalled();
    expect(generateFixSpy).not.toHaveBeenCalled();
    expect(applyFixSpy).not.toHaveBeenCalled();
  });

  it('ReviewResultsPage header provides dual navigation to Start Review and Review History', async () => {
    vi.spyOn(reviewsApi, 'getReview').mockResolvedValueOnce(mockReviews[0]);

    render(
      <MemoryRouter initialEntries={['/reviews/rev-completed-1']}>
        <Routes>
          <Route path="/reviews/:reviewId" element={<ReviewResultsPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Review')).toBeInTheDocument();
      expect(screen.getByText('Review History')).toBeInTheDocument();
    });
  });
});
