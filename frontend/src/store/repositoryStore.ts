import { create } from 'zustand';
import {
  repositoriesApi,
  RepositoryCreateParams,
  RepositoryUpdateParams,
  RepositoryListQueryParams,
  RepositoryIndexStatus,
} from '../api/repositories';
import { Repository } from '../types';

interface RepositoryStoreState {
  repositories: Repository[];
  selectedRepo: Repository | null;
  indexingStatusMap: Record<string, RepositoryIndexStatus>;
  isLoading: boolean;
  isImporting: boolean;
  error: string | null;

  fetchRepositories: (params?: RepositoryListQueryParams) => Promise<void>;
  fetchRepository: (id: string) => Promise<Repository>;
  importRepository: (data: RepositoryCreateParams) => Promise<Repository>;
  fetchIndexStatus: (id: string) => Promise<RepositoryIndexStatus>;
  reindexRepository: (id: string) => Promise<RepositoryIndexStatus>;
  updateRepository: (id: string, data: RepositoryUpdateParams) => Promise<Repository>;
  deleteRepository: (id: string) => Promise<void>;
  refreshRepository: (id: string) => Promise<Repository>;
  switchBranch: (id: string, branch: string) => Promise<Repository>;
  setSelectedRepo: (repo: Repository | null) => void;
}

export const useRepositoryStore = create<RepositoryStoreState>((set, _get) => ({
  repositories: [],
  selectedRepo: null,
  indexingStatusMap: {},
  isLoading: false,
  isImporting: false,
  error: null,

  fetchRepositories: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const repos = await repositoriesApi.getRepositories(params);
      set({ repositories: repos, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch repositories', isLoading: false });
    }
  },

  fetchRepository: async (id) => {
    try {
      const repo = await repositoriesApi.getRepository(id);
      set({ selectedRepo: repo });
      return repo;
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch repository details' });
      throw err;
    }
  },

  importRepository: async (data) => {
    set({ isImporting: true, error: null });
    try {
      const newRepo = await repositoriesApi.importRepository(data);
      set((state) => ({
        repositories: [newRepo, ...state.repositories],
        selectedRepo: newRepo,
        isImporting: false,
      }));
      return newRepo;
    } catch (err: any) {
      set({ error: err.message || 'Failed to import repository', isImporting: false });
      throw err;
    }
  },

  fetchIndexStatus: async (id) => {
    try {
      const status = await repositoriesApi.getIndexStatus(id);
      set((state) => ({
        indexingStatusMap: {
          ...state.indexingStatusMap,
          [id]: status,
        },
        // If the selected repository status changes, update it
        selectedRepo:
          state.selectedRepo?.id === id
            ? {
                ...state.selectedRepo,
                indexing_status: (status.status as any),
                chunks_count: status.chunks_created,
              }
            : state.selectedRepo,
        // Update list status as well
        repositories: state.repositories.map((r) =>
          r.id === id
            ? {
                ...r,
                indexing_status: (status.status as any),
                chunks_count: status.chunks_created,
              }
            : r
        ),
      }));
      return status;
    } catch (err: any) {
      console.warn(`Failed to fetch indexing status for repo ${id}:`, err);
      throw err;
    }
  },

  reindexRepository: async (id) => {
    try {
      const status = await repositoriesApi.reindexRepository(id);
      set((state) => ({
        indexingStatusMap: {
          ...state.indexingStatusMap,
          [id]: status,
        },
        repositories: state.repositories.map((r) =>
          r.id === id ? { ...r, indexing_status: 'indexing' as any } : r
        ),
        selectedRepo:
          state.selectedRepo?.id === id
            ? { ...state.selectedRepo, indexing_status: 'indexing' as any }
            : state.selectedRepo,
      }));
      return status;
    } catch (err: any) {
      set({ error: err.message || 'Failed to trigger re-indexing' });
      throw err;
    }
  },

  updateRepository: async (id, data) => {
    try {
      const updated = await repositoriesApi.updateRepository(id, data);
      set((state) => ({
        repositories: state.repositories.map((r) => (r.id === id ? updated : r)),
        selectedRepo: state.selectedRepo?.id === id ? updated : state.selectedRepo,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to update repository' });
      throw err;
    }
  },

  deleteRepository: async (id) => {
    try {
      await repositoriesApi.deleteRepository(id);
      set((state) => ({
        repositories: state.repositories.filter((r) => r.id !== id),
        selectedRepo: state.selectedRepo?.id === id ? null : state.selectedRepo,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete repository' });
      throw err;
    }
  },

  refreshRepository: async (id) => {
    try {
      const refreshed = await repositoriesApi.refreshRepository(id);
      set((state) => ({
        repositories: state.repositories.map((r) => (r.id === id ? refreshed : r)),
        selectedRepo: state.selectedRepo?.id === id ? refreshed : state.selectedRepo,
      }));
      return refreshed;
    } catch (err: any) {
      set({ error: err.message || 'Failed to refresh repository' });
      throw err;
    }
  },

  switchBranch: async (id, branch) => {
    try {
      const updated = await repositoriesApi.switchBranch(id, branch);
      set((state) => ({
        repositories: state.repositories.map((r) => (r.id === id ? updated : r)),
        selectedRepo: state.selectedRepo?.id === id ? updated : state.selectedRepo,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to switch branch' });
      throw err;
    }
  },

  setSelectedRepo: (repo) => set({ selectedRepo: repo }),
}));
