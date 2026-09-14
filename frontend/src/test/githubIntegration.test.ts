import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { integrationsApi } from '../api/integrations';
import { useGitHubStore } from '../store/useGitHubStore';

describe('GitHub Integration Disconnect & Reconnect Store/API', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
    useGitHubStore.setState({
      status: { connected: true, username: 'octocat', avatar_url: 'https://avatars.github.com/u/1', connected_at: '2026-01-01' },
      isStatusLoading: false,
      statusError: null,
      isExpired: false,
      repositories: [
        {
          id: '101',
          name: 'my-repo',
          full_name: 'octocat/my-repo',
          owner: 'octocat',
          url: 'https://github.com/octocat/my-repo',
          clone_url: 'https://github.com/octocat/my-repo.git',
          is_private: false,
          default_branch: 'main',
          description: 'A test repo',
          stars: 10,
          language: 'TypeScript',
          updated_at: '2026-09-01',
        },
      ],
      isReposLoading: false,
      reposError: null,
      reposPage: 1,
      reposSearch: '',
      hasMore: true,
      isConnecting: false,
      isDisconnecting: false,
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('disconnectGitHub sends DELETE to /api/v1/integrations/github/disconnect', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ connected: false, message: 'GitHub account disconnected successfully' }),
    });

    const res = await integrationsApi.disconnectGitHub();
    expect(res).toEqual({ connected: false, message: 'GitHub account disconnected successfully' });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/integrations\/github\/disconnect$/),
      expect.objectContaining({ method: 'DELETE' })
    );
  });

  it('useGitHubStore.disconnect clears connection status and repositories', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ connected: false, message: 'Disconnected' }),
    });

    await useGitHubStore.getState().disconnect();

    const state = useGitHubStore.getState();
    expect(state.status?.connected).toBe(false);
    expect(state.status?.username).toBeNull();
    expect(state.repositories).toEqual([]);
    expect(state.isExpired).toBe(false);
    expect(state.isDisconnecting).toBe(false);
  });

  it('useGitHubStore.fetchRepositories sets isExpired to true on 401 response', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Your GitHub connection has expired. Please reconnect GitHub.' }),
    });

    await useGitHubStore.getState().fetchRepositories({ page: 1 });

    const state = useGitHubStore.getState();
    expect(state.isExpired).toBe(true);
    expect(state.reposError).toBe('Your GitHub connection has expired. Please reconnect GitHub.');
  });
});
