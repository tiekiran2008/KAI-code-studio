import { fetchClient } from './fetchClient';
import { Project, ProjectDashboard } from '../types';

export interface ProjectCreateParams {
  name: string;
  description?: string;
  workspace_id?: string;
  repository_ids?: string[];
}

export interface ProjectUpdateParams {
  name?: string;
  description?: string;
  workspace_id?: string;
}

export const projectsApi = {
  async getProjects(workspace_id?: string): Promise<Project[]> {
    return fetchClient.get<Project[]>('/projects', { params: { workspace_id } });
  },

  async getProject(id: string): Promise<Project> {
    return fetchClient.get<Project>(`/projects/${id}`);
  },

  async createProject(data: ProjectCreateParams): Promise<Project> {
    return fetchClient.post<Project>('/projects', data);
  },

  async updateProject(id: string, data: ProjectUpdateParams): Promise<Project> {
    return fetchClient.put<Project>(`/projects/${id}`, data);
  },

  async archiveProject(id: string): Promise<Project> {
    return fetchClient.post<Project>(`/projects/${id}/archive`);
  },

  async deleteProject(id: string): Promise<void> {
    return fetchClient.delete(`/projects/${id}`);
  },

  async linkRepository(projectId: string, repoId: string): Promise<Project> {
    return fetchClient.post<Project>(`/projects/${projectId}/repositories/${repoId}`);
  },

  async unlinkRepository(projectId: string, repoId: string): Promise<Project> {
    return fetchClient.delete<Project>(`/projects/${projectId}/repositories/${repoId}`);
  },

  async getDashboard(id: string): Promise<ProjectDashboard> {
    return fetchClient.get<ProjectDashboard>(`/projects/${id}/dashboard`);
  }
};
