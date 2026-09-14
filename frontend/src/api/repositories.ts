import { fetchClient } from './fetchClient';
import { Repository, RepositoryProvider, IndexingStatus, FileNode } from '../types';

export interface FileContentResponse {
  path: string;
  name: string;
  content: string;
  size: number;
  language: string;
  is_binary: boolean;
}

export interface RepositoryCreateParams {
  url: string;
  provider?: RepositoryProvider;
  name?: string;
  description?: string;
  default_branch?: string;
  workspace_id?: string;
  git_access_token?: string;
}

export interface RepositoryUpdateParams {
  name?: string;
  description?: string;
  default_branch?: string;
  workspace_id?: string;
}

export interface RepositoryListQueryParams {
  workspace_id?: string;
  provider?: RepositoryProvider;
  indexing_status?: IndexingStatus;
  search?: string;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_dir?: string;
}

export interface RepositoryHealthCheckResponse {
  repo_id: string;
  is_reachable: boolean;
  latency_ms?: number;
  error?: string;
  checked_at: string;
}

export interface RepositoryIndexStatus {
  repository_id: string;
  status: IndexingStatus | string;
  stage: string;
  progress: number;
  files_discovered: number;
  files_processed: number;
  chunks_created: number;
  error?: string | null;
  started_at?: string;
  completed_at?: string;
}

export const repositoriesApi = {
  async getRepositories(params?: RepositoryListQueryParams): Promise<Repository[]> {
    return fetchClient.get<Repository[]>('/repositories', { params: params as any });
  },

  async getRepository(id: string): Promise<Repository> {
    return fetchClient.get<Repository>(`/repositories/${id}`);
  },

  async importRepository(data: RepositoryCreateParams): Promise<Repository> {
    return fetchClient.post<Repository>('/repositories/import', data);
  },

  async getIndexStatus(id: string): Promise<RepositoryIndexStatus> {
    return fetchClient.get<RepositoryIndexStatus>(`/repositories/${id}/index-status`);
  },

  async reindexRepository(id: string): Promise<RepositoryIndexStatus> {
    return fetchClient.post<RepositoryIndexStatus>(`/repositories/${id}/reindex`);
  },

  async updateRepository(id: string, data: RepositoryUpdateParams): Promise<Repository> {
    return fetchClient.put<Repository>(`/repositories/${id}`, data);
  },

  async deleteRepository(id: string): Promise<void> {
    return fetchClient.delete(`/repositories/${id}`);
  },

  async refreshRepository(id: string): Promise<Repository> {
    return fetchClient.post<Repository>(`/repositories/${id}/refresh`);
  },

  async getHealthCheck(id: string): Promise<RepositoryHealthCheckResponse> {
    return fetchClient.get<RepositoryHealthCheckResponse>(`/repositories/${id}/health`);
  },

  async getBranches(id: string): Promise<string[]> {
    return fetchClient.get<string[]>(`/repositories/${id}/branches`);
  },

  async switchBranch(id: string, branch: string): Promise<Repository> {
    return fetchClient.patch<Repository>(`/repositories/${id}/branch`, { branch });
  },

  async getFileTree(id: string): Promise<FileNode[]> {
    return fetchClient.get<FileNode[]>(`/repositories/${id}/tree`);
  },

  async getFileContent(id: string, path: string): Promise<FileContentResponse> {
    return fetchClient.get<FileContentResponse>(`/repositories/${id}/files/content`, {
      params: { path },
    });
  },
};

