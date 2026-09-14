/**
 * GitHub Integration API Client
 * ================================
 * Typed API functions for the /integrations/github endpoints.
 * All calls go through the authenticated fetchClient.
 * Tokens are never exposed to or stored in the frontend.
 */
import { fetchClient } from './fetchClient';

// ─── Response types ───────────────────────────────────────────────────────────

export interface GitHubStatus {
  connected: boolean;
  username: string | null;
  avatar_url: string | null;
  connected_at: string | null;
}

export interface GitHubConnectResponse {
  auth_url: string;
}

export interface GitHubRepository {
  id: string;
  name: string;
  full_name: string;
  owner: string;
  url: string;
  clone_url: string;
  is_private: boolean;
  default_branch: string;
  description: string | null;
  stars: number;
  language: string | null;
  updated_at: string | null;
}

export interface GitHubRepositoryListParams {
  page?: number;
  per_page?: number;
  search?: string;
}

// ─── API Functions ─────────────────────────────────────────────────────────────

export const integrationsApi = {
  /**
   * Fetch the current GitHub connection status for the authenticated user.
   * Safe to call on mount — returns { connected: false } if not linked.
   */
  async getGitHubStatus(): Promise<GitHubStatus> {
    return fetchClient.get<GitHubStatus>('/integrations/github/status');
  },

  /**
   * Retrieve the OAuth authorization URL.
   * The frontend redirects the user's browser to this URL.
   */
  async getGitHubConnectUrl(): Promise<GitHubConnectResponse> {
    return fetchClient.get<GitHubConnectResponse>('/integrations/github/connect');
  },

  /**
   * Disconnect the linked GitHub account and remove all stored tokens.
   */
  async disconnectGitHub(): Promise<{ connected: boolean; message: string }> {
    return fetchClient.delete('/integrations/github/disconnect');
  },

  /**
   * List GitHub repositories accessible to the connected account.
   */
  async listGitHubRepositories(
    params: GitHubRepositoryListParams = {},
  ): Promise<GitHubRepository[]> {
    return fetchClient.get<GitHubRepository[]>('/integrations/github/repositories', {
      params: {
        page: params.page ?? 1,
        per_page: params.per_page ?? 30,
        ...(params.search ? { search: params.search } : {}),
      } as any,
    });
  },
};
