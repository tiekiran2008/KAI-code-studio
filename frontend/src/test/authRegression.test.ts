import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchClient, getAuthToken } from '../api/fetchClient';
import { useAuthStore } from '../store/authStore';

// Mock Supabase module
const mockGetSession = vi.fn();
const mockSignOut = vi.fn();
const mockSignInWithOAuth = vi.fn();
const mockOnAuthStateChange = vi.fn().mockReturnValue({
  data: { subscription: { unsubscribe: vi.fn() } },
});

vi.mock('../lib/supabase', () => ({
  isSupabaseConfigured: true,
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      signOut: () => mockSignOut(),
      signInWithOAuth: (args: any) => mockSignInWithOAuth(args),
      onAuthStateChange: (cb: any) => mockOnAuthStateChange(cb),
    },
  },
}));

describe('Production Auth & Preflight Regressions', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    globalThis.fetch = vi.fn() as any;
    mockGetSession.mockResolvedValue({ data: { session: null }, error: null });
    mockSignOut.mockResolvedValue({ error: null });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    localStorage.clear();
  });

  it('1. GitHub OAuth login triggers Supabase signInWithOAuth with correct redirectTo origin', async () => {
    mockSignInWithOAuth.mockResolvedValueOnce({ error: null });
    await useAuthStore.getState().loginWithOAuth('github');

    expect(mockSignInWithOAuth).toHaveBeenCalledWith({
      provider: 'github',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  });

  it('2. Authenticated fetchClient calls use the CURRENT Supabase session access_token', async () => {
    const liveSupabaseToken = 'sb-live-jwt-token-active';
    mockGetSession.mockResolvedValue({
      data: {
        session: {
          access_token: liveSupabaseToken,
          refresh_token: 'sb-refresh-123',
          expires_in: 3600,
          user: { id: 'sb-user-1', email: 'user@example.com' },
        },
      },
      error: null,
    });

    // Even if an old stale token exists in localStorage, current Supabase token must take precedence
    localStorage.setItem('access_token', 'old-stale-token');

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ status: 'success' }),
    });

    const token = await getAuthToken();
    expect(token).toBe(liveSupabaseToken);

    await fetchClient.get('/profile');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': `Bearer ${liveSupabaseToken}`,
        }),
      })
    );
  });

  it('3. fetchClient does NOT globally inject X-User-ID to avoid CORS preflight 400', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: {
        session: {
          access_token: 'valid-jwt',
          user: { id: 'usr-12345' },
        },
      },
      error: null,
    });

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ ok: true }),
    });

    await fetchClient.get('/workspaces');
    const calledHeaders = (globalThis.fetch as any).mock.calls[0][1]?.headers;

    expect(calledHeaders['Authorization']).toBe('Bearer valid-jwt');
    expect(calledHeaders['X-User-ID']).toBeUndefined();
    expect(calledHeaders['x-user-id']).toBeUndefined();
  });

  it('4. Logout gracefully handles already-invalid or expired sessions without throwing', async () => {
    mockSignOut.mockRejectedValueOnce(new Error('Session from session_id claim in JWT does not exist'));

    (globalThis.fetch as any).mockRejectedValueOnce(new Error('403 Forbidden: Invalid session'));

    useAuthStore.setState({
      accessToken: 'expired-token',
      isAuthenticated: true,
      user: { id: 'usr-1', email: 'test@example.com', created_at: '' },
    });
    localStorage.setItem('access_token', 'expired-token');

    // Should complete cleanly without uncaught exception
    await expect(useAuthStore.getState().logout()).resolves.toBeUndefined();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
  });
});
