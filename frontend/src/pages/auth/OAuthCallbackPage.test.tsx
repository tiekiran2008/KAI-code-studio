import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { OAuthCallbackPage } from './OAuthCallbackPage';
import { useAuthStore } from '../../store/authStore';

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}));

// Mock supabase and related lib
vi.mock('../../lib/supabase', () => ({
  supabase: null,
  isSupabaseConfigured: false,
}));

vi.mock('../../api/profile', () => ({
  profileApi: {
    getProfile: vi.fn(),
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('OAuthCallbackPage Component', () => {
  const mockSetOAuthSession = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as any).mockReturnValue({
      setOAuthSession: mockSetOAuthSession,
    });
  });

  it('renders loading state with Completing Sign In heading by default', () => {
    render(
      <MemoryRouter initialEntries={['/auth/callback']}>
        <OAuthCallbackPage />
      </MemoryRouter>
    );

    // During loading the component shows the "Completing Sign In" heading
    expect(screen.getByText('Completing Sign In')).toBeInTheDocument();
  });

  it('renders Sign In Failed and Back to Sign In button when error query param is present', async () => {
    render(
      <MemoryRouter initialEntries={['/auth/callback?error=access_denied&error_description=User+denied+access']}>
        <OAuthCallbackPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Sign In Failed')).toBeInTheDocument();
    });

    expect(screen.getByText('User denied access')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Back to Sign In/i })).toBeInTheDocument();
  });

  it('redirects to / when supabase is not configured (dev fallback)', async () => {
    render(
      <MemoryRouter initialEntries={['/auth/callback']}>
        <OAuthCallbackPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockSetOAuthSession).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('sets user session and redirects to / on successful OAuth callback', async () => {
    render(
      <MemoryRouter initialEntries={['/auth/callback?code=mock-auth-code']}>
        <OAuthCallbackPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockSetOAuthSession).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });
});
