/**
 * GitHub Integration Store
 * ==========================
 * Zustand store that manages:
 * - GitHub connection status polling
 * - OAuth redirect initiation
 * - Disconnect flow
 * - GitHub repository listing with search/pagination
 *
 * Tokens are NEVER stored here; only non-sensitive metadata
 * returned from the backend status endpoint is held in state.
 */
import { create } from 'zustand';
import {
  integrationsApi,
  GitHubStatus,
  GitHubRepository,
  GitHubRepositoryListParams,
} from '../api/integrations';

interface GitHubStoreState {
  // Connection status
  status: GitHubStatus | null;
  isStatusLoading: boolean;
  statusError: string | null;

  // Repository listing
  repositories: GitHubRepository[];
  isReposLoading: boolean;
  reposError: string | null;
  reposPage: number;
  reposSearch: string;
  hasMore: boolean;

  // OAuth connect / disconnect loading
  isConnecting: boolean;
  isDisconnecting: boolean;

  // Actions
  fetchStatus: () => Promise<void>;
  startOAuthFlow: () => Promise<void>;
  disconnect: () => Promise<void>;
  fetchRepositories: (params?: GitHubRepositoryListParams) => Promise<void>;
  loadMoreRepositories: () => Promise<void>;
  setReposSearch: (search: string) => void;
  resetRepos: () => void;
}

export const useGitHubStore = create<GitHubStoreState>((set, get) => ({
  // ─── Initial state ────────────────────────────────────────────────────────
  status: null,
  isStatusLoading: false,
  statusError: null,

  repositories: [],
  isReposLoading: false,
  reposError: null,
  reposPage: 1,
  reposSearch: '',
  hasMore: true,

  isConnecting: false,
  isDisconnecting: false,

  // ─── Actions ──────────────────────────────────────────────────────────────

  /** Fetch (or refresh) the GitHub connection status from the backend. */
  fetchStatus: async () => {
    set({ isStatusLoading: true, statusError: null });
    try {
      const status = await integrationsApi.getGitHubStatus();
      set({ status, isStatusLoading: false });
    } catch (err: any) {
      set({
        statusError: err.message || 'Failed to fetch GitHub status',
        isStatusLoading: false,
      });
    }
  },

  /**
   * Kick off the GitHub OAuth flow.
   * Fetches the backend-generated auth URL and redirects the browser.
   * The backend callback will exchange the code and redirect back to /settings.
   */
  startOAuthFlow: async () => {
    set({ isConnecting: true, statusError: null });
    try {
      const { auth_url } = await integrationsApi.getGitHubConnectUrl();
      window.location.href = auth_url;
      // isConnecting will reset naturally after page redirect
    } catch (err: any) {
      set({
        statusError: err.message || 'Failed to initiate GitHub connection',
        isConnecting: false,
      });
    }
  },

  /** Disconnect the GitHub integration and clear local state. */
  disconnect: async () => {
    set({ isDisconnecting: true, statusError: null });
    try {
      await integrationsApi.disconnectGitHub();
      set({
        status: { connected: false, username: null, avatar_url: null, connected_at: null },
        repositories: [],
        reposPage: 1,
        hasMore: true,
        isDisconnecting: false,
      });
    } catch (err: any) {
      set({
        statusError: err.message || 'Failed to disconnect GitHub',
        isDisconnecting: false,
      });
    }
  },

  /**
   * Fetch the first page of GitHub repositories, replacing existing list.
   * Optionally accepts search / page override.
   */
  fetchRepositories: async (params = {}) => {
    const { reposSearch } = get();
    const page = params.page ?? 1;
    const search = params.search ?? reposSearch;

    set({ isReposLoading: true, reposError: null, reposPage: page });
    try {
      const repos = await integrationsApi.listGitHubRepositories({
        page,
        per_page: 30,
        search: search || undefined,
      });
      set({
        repositories: page === 1 ? repos : [...get().repositories, ...repos],
        isReposLoading: false,
        hasMore: repos.length === 30,
      });
    } catch (err: any) {
      set({
        reposError: err.message || 'Failed to fetch repositories',
        isReposLoading: false,
      });
    }
  },

  /** Append the next page to the existing list. */
  loadMoreRepositories: async () => {
    const { reposPage, isReposLoading, hasMore, reposSearch } = get();
    if (isReposLoading || !hasMore) return;

    const nextPage = reposPage + 1;
    set({ reposPage: nextPage });
    const repos = await integrationsApi.listGitHubRepositories({
      page: nextPage,
      per_page: 30,
      search: reposSearch || undefined,
    });
    set((state) => ({
      repositories: [...state.repositories, ...repos],
      hasMore: repos.length === 30,
      isReposLoading: false,
    }));
  },

  /** Update search term (caller is responsible for triggering fetchRepositories). */
  setReposSearch: (search) => set({ reposSearch: search }),

  /** Clear the repository list (e.g. when unmounting the picker). */
  resetRepos: () => set({ repositories: [], reposPage: 1, hasMore: true, reposError: null }),
}));
