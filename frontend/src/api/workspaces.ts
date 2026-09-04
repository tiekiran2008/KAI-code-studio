import { fetchClient } from './fetchClient';

export interface Workspace {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  default_ai_model: string;
  default_repo_id: string | null;
  vector_db_config: Record<string, any>;
  tool_config: Record<string, any>;
  repo_count: number;
  created_at: string;
  updated_at: string;
}

export type WorkspaceCreate = Pick<Workspace, 'name' | 'description' | 'default_ai_model' | 'default_repo_id' | 'vector_db_config' | 'tool_config'>;
export type WorkspaceUpdate = Partial<WorkspaceCreate>;

export const workspacesApi = {
  async getWorkspaces(): Promise<Workspace[]> {
    return fetchClient.get<Workspace[]>('/workspaces');
  },

  async getWorkspace(id: string): Promise<Workspace> {
    return fetchClient.get<Workspace>(`/workspaces/${id}`);
  },

  async createWorkspace(data: WorkspaceCreate): Promise<Workspace> {
    return fetchClient.post<Workspace>('/workspaces', data);
  },

  async updateWorkspace(id: string, data: WorkspaceUpdate): Promise<Workspace> {
    return fetchClient.put<Workspace>(`/workspaces/${id}`, data);
  },

  async deleteWorkspace(id: string): Promise<void> {
    return fetchClient.delete(`/workspaces/${id}`);
  }
};
