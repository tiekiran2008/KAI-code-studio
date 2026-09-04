import { create } from 'zustand';
import { projectsApi, ProjectCreateParams, ProjectUpdateParams } from '../api/projects';
import { Project, ProjectDashboard } from '../types';

interface ProjectStoreState {
  projects: Project[];
  activeProject: Project | null;
  dashboard: ProjectDashboard | null;
  isLoading: boolean;
  error: string | null;

  fetchProjects: (workspace_id?: string) => Promise<void>;
  fetchProject: (id: string) => Promise<Project>;
  createProject: (data: ProjectCreateParams) => Promise<Project>;
  updateProject: (id: string, data: ProjectUpdateParams) => Promise<Project>;
  archiveProject: (id: string) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
  linkRepository: (projectId: string, repoId: string) => Promise<Project>;
  unlinkRepository: (projectId: string, repoId: string) => Promise<Project>;
  fetchDashboard: (id: string) => Promise<ProjectDashboard>;
}

export const useProjectStore = create<ProjectStoreState>((set) => ({
  projects: [],
  activeProject: null,
  dashboard: null,
  isLoading: false,
  error: null,

  fetchProjects: async (workspace_id) => {
    set({ isLoading: true, error: null });
    try {
      const list = await projectsApi.getProjects(workspace_id);
      set({ projects: list, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch projects', isLoading: false });
    }
  },

  fetchProject: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectsApi.getProject(id);
      set({ activeProject: project, isLoading: false });
      return project;
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch project', isLoading: false });
      throw err;
    }
  },

  createProject: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectsApi.createProject(data);
      set((state) => ({
        projects: [project, ...state.projects],
        isLoading: false,
      }));
      return project;
    } catch (err: any) {
      set({ error: err.message || 'Failed to create project', isLoading: false });
      throw err;
    }
  },

  updateProject: async (id, data) => {
    try {
      const updated = await projectsApi.updateProject(id, data);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === id ? updated : p)),
        activeProject: state.activeProject?.id === id ? updated : state.activeProject,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to update project' });
      throw err;
    }
  },

  archiveProject: async (id) => {
    try {
      const archived = await projectsApi.archiveProject(id);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === id ? archived : p)),
        activeProject: state.activeProject?.id === id ? archived : state.activeProject,
      }));
      return archived;
    } catch (err: any) {
      set({ error: err.message || 'Failed to archive project' });
      throw err;
    }
  },

  deleteProject: async (id) => {
    try {
      await projectsApi.deleteProject(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        activeProject: state.activeProject?.id === id ? null : state.activeProject,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete project' });
      throw err;
    }
  },

  linkRepository: async (projectId, repoId) => {
    try {
      const updated = await projectsApi.linkRepository(projectId, repoId);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === projectId ? updated : p)),
        activeProject: state.activeProject?.id === projectId ? updated : state.activeProject,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to link repository' });
      throw err;
    }
  },

  unlinkRepository: async (projectId, repoId) => {
    try {
      const updated = await projectsApi.unlinkRepository(projectId, repoId);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === projectId ? updated : p)),
        activeProject: state.activeProject?.id === projectId ? updated : state.activeProject,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to unlink repository' });
      throw err;
    }
  },

  fetchDashboard: async (id) => {
    try {
      const dashboard = await projectsApi.getDashboard(id);
      set({ dashboard });
      return dashboard;
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch project dashboard' });
      throw err;
    }
  },
}));
