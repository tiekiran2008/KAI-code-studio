import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getApiBaseUrl, buildApiUrl, fetchClient } from '../api/fetchClient';
import { workspacesApi } from '../api/workspaces';
import { projectsApi } from '../api/projects';
import { repositoriesApi } from '../api/repositories';
import { integrationsApi } from '../api/integrations';
import { reviewsApi } from '../api/reviews';
import { authApi } from '../api/auth';

describe('Centralized API Base URL and Endpoint Routing', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('buildApiUrl produces canonical /api/v1 URL without double prefix', () => {
    const baseUrl = getApiBaseUrl();
    expect(baseUrl).toContain('/api/v1');

    expect(buildApiUrl('/workspaces')).toBe(`${baseUrl}/workspaces`);
    expect(buildApiUrl('workspaces')).toBe(`${baseUrl}/workspaces`);
    expect(buildApiUrl('/api/v1/workspaces')).toBe(`${baseUrl}/workspaces`);
    expect(buildApiUrl('/projects')).toBe(`${baseUrl}/projects`);
    expect(buildApiUrl('/repositories')).toBe(`${baseUrl}/repositories`);
  });

  it('workspacesApi makes requests to /api/v1/workspaces', async () => {
    const mockWorkspaces = [{ id: 'ws-1', name: 'Workspace 1' }];
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockWorkspaces,
    });

    const res = await workspacesApi.getWorkspaces();
    expect(res).toEqual(mockWorkspaces);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/workspaces$/),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('workspacesApi.createWorkspace sends POST to /api/v1/workspaces', async () => {
    const newWs = { id: 'ws-2', name: 'New WS' };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => newWs,
    });

    const res = await workspacesApi.createWorkspace({
      name: 'New WS',
      description: 'Desc',
      default_ai_model: 'gpt-4o',
      default_repo_id: null,
      vector_db_config: {},
      tool_config: {},
    });
    expect(res).toEqual(newWs);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/workspaces$/),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'New WS',
          description: 'Desc',
          default_ai_model: 'gpt-4o',
          default_repo_id: null,
          vector_db_config: {},
          tool_config: {},
        }),
      })
    );
  });

  it('projectsApi makes requests to /api/v1/projects with query params', async () => {
    const mockProjects = [{ id: 'proj-1', name: 'Project 1' }];
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockProjects,
    });

    const res = await projectsApi.getProjects('ws-123');
    expect(res).toEqual(mockProjects);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/projects\?workspace_id=ws-123$/),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('projectsApi.createProject sends POST to /api/v1/projects', async () => {
    const newProj = { id: 'proj-2', name: 'New Project' };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => newProj,
    });

    const res = await projectsApi.createProject({
      name: 'New Project',
      description: 'Test Description',
      workspace_id: 'ws-123',
    });
    expect(res).toEqual(newProj);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/projects$/),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          name: 'New Project',
          description: 'Test Description',
          workspace_id: 'ws-123',
        }),
      })
    );
  });

  it('repositoriesApi.importRepository sends POST to /api/v1/repositories/import', async () => {
    const mockRepo = { id: 'repo-1', name: 'test-repo', url: 'https://github.com/org/repo' };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockRepo,
    });

    const res = await repositoriesApi.importRepository({
      url: 'https://github.com/org/repo',
      default_branch: 'main',
    });
    expect(res).toEqual(mockRepo);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/repositories\/import$/),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('repositoriesApi.reindexRepository sends POST to /api/v1/repositories/{id}/reindex (not /refresh)', async () => {
    const repoId = 'repo-abc-123';
    const mockStatus = {
      repository_id: repoId,
      status: 'indexing',
      stage: 'cloning',
      progress: 5.0,
      files_discovered: 0,
      files_processed: 0,
      chunks_created: 0,
    };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockStatus,
    });

    const res = await repositoriesApi.reindexRepository(repoId);
    expect(res).toEqual(mockStatus);
    // Must hit /reindex, NOT /refresh
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(new RegExp(`/api/v1/repositories/${repoId}/reindex$`)),
      expect.objectContaining({ method: 'POST' })
    );
    // Confirm /refresh was NOT called
    expect(globalThis.fetch).not.toHaveBeenCalledWith(
      expect.stringMatching(/\/refresh$/),
      expect.anything()
    );
  });

  it('repositoriesApi.getIndexStatus sends GET to /api/v1/repositories/{id}/index-status', async () => {
    const repoId = 'repo-xyz-789';
    const mockStatus = {
      repository_id: repoId,
      status: 'indexed',
      stage: 'complete',
      progress: 100,
      files_discovered: 42,
      files_processed: 42,
      chunks_created: 380,
    };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockStatus,
    });

    const res = await repositoriesApi.getIndexStatus(repoId);
    expect(res).toEqual(mockStatus);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(new RegExp(`/api/v1/repositories/${repoId}/index-status$`)),
      expect.objectContaining({ method: 'GET' })
    );
  });


  it('integrationsApi routes to /api/v1/integrations/github/status', async () => {
    const mockStatus = { connected: true, username: 'octocat', avatar_url: null, connected_at: null };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockStatus,
    });

    const res = await integrationsApi.getGitHubStatus();
    expect(res).toEqual(mockStatus);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/integrations\/github\/status$/),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('reviewsApi routes to /api/v1/reviews/start', async () => {
    const mockStart = { message: 'Started', review_id: 'rev-123' };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockStart,
    });

    const res = await reviewsApi.startReview({ repository_id: 'repo-1' });
    expect(res).toEqual(mockStart);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/reviews\/start$/),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('authApi routes to /api/v1/auth/login and /api/v1/auth/me', async () => {
    const mockSession = { user: { id: 'u-1', email: 'test@example.com' }, access_token: 'token-123' };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockSession,
    });

    const res = await authApi.login('test@example.com', 'secret');
    expect(res).toEqual(mockSession);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/auth\/login$/),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('ApiError properly extracts structured validation errors from FastAPI response', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        detail: [
          { loc: ['body', 'name'], msg: 'Field required' },
          { loc: ['body', 'url'], msg: 'Invalid URL' },
        ],
      }),
    });

    await expect(fetchClient.get('/test')).rejects.toThrow('Field required, Invalid URL');
  });

  it('attaches X-User-ID and Authorization headers from localStorage access_token', async () => {
    localStorage.setItem('access_token', 'jwt-token-xyz');
    localStorage.setItem('user', JSON.stringify({ id: 'usr-custom-42' }));

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ ok: true }),
    });

    await fetchClient.get('/workspaces');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer jwt-token-xyz',
          'X-User-ID': 'usr-custom-42',
        }),
      })
    );
  });

  it('attaches Authorization Bearer token from Zustand auth-storage when flat key is missing', async () => {
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          accessToken: 'zustand-oauth-jwt-token',
          user: { id: 'usr-oauth-99', email: 'user@kaistudio.dev' },
        },
      })
    );

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ ok: true }),
    });

    await fetchClient.get('/profile');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer zustand-oauth-jwt-token',
          'X-User-ID': 'usr-oauth-99',
        }),
      })
    );
  });

  it('does NOT attach Authorization header when unauthenticated (no token in storage)', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ ok: true }),
    });

    await fetchClient.get('/public-endpoint');
    const calledHeaders = (globalThis.fetch as any).mock.calls[0][1]?.headers;
    expect(calledHeaders?.Authorization).toBeUndefined();
    expect(calledHeaders?.authorization).toBeUndefined();
  });

  it('preserves caller-supplied Authorization header without overwriting', async () => {
    localStorage.setItem('access_token', 'default-token');

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ ok: true }),
    });

    await fetchClient.get('/custom', {
      headers: { Authorization: 'Bearer custom-explicit-token' },
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer custom-explicit-token',
        }),
      })
    );
  });
});
