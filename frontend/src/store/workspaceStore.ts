import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { workspacesApi, Workspace, WorkspaceCreate, WorkspaceUpdate } from '../api/workspaces';

interface WorkspaceState {
  workspaces: Workspace[];
  activeWorkspaceId: string | null;
  isLoading: boolean;
  error: string | null;

  fetchWorkspaces: () => Promise<void>;
  createWorkspace: (data: WorkspaceCreate) => Promise<Workspace>;
  updateWorkspace: (id: string, data: WorkspaceUpdate) => Promise<Workspace>;
  deleteWorkspace: (id: string) => Promise<void>;
  setActiveWorkspace: (id: string) => void;
  getActiveWorkspace: () => Workspace | undefined;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      workspaces: [],
      activeWorkspaceId: null,
      isLoading: false,
      error: null,

      fetchWorkspaces: async () => {
        set({ isLoading: true, error: null });
        try {
          const workspaces = await workspacesApi.getWorkspaces();
          set({ workspaces, isLoading: false });
        } catch (error: any) {
          set({ error: error.message || 'Failed to fetch workspaces', isLoading: false });
        }
      },

      createWorkspace: async (data) => {
        set({ isLoading: true, error: null });
        try {
          const workspace = await workspacesApi.createWorkspace(data);
          set(state => ({ 
            workspaces: [...state.workspaces, workspace],
            isLoading: false 
          }));
          return workspace;
        } catch (error: any) {
          set({ error: error.message || 'Failed to create workspace', isLoading: false });
          throw error;
        }
      },

      updateWorkspace: async (id, data) => {
        set({ isLoading: true, error: null });
        try {
          const workspace = await workspacesApi.updateWorkspace(id, data);
          set(state => ({
            workspaces: state.workspaces.map(w => w.id === id ? workspace : w),
            isLoading: false
          }));
          return workspace;
        } catch (error: any) {
          set({ error: error.message || 'Failed to update workspace', isLoading: false });
          throw error;
        }
      },

      deleteWorkspace: async (id) => {
        set({ isLoading: true, error: null });
        try {
          await workspacesApi.deleteWorkspace(id);
          set(state => ({
            workspaces: state.workspaces.filter(w => w.id !== id),
            activeWorkspaceId: state.activeWorkspaceId === id ? null : state.activeWorkspaceId,
            isLoading: false
          }));
        } catch (error: any) {
          set({ error: error.message || 'Failed to delete workspace', isLoading: false });
          throw error;
        }
      },

      setActiveWorkspace: (id) => {
        set({ activeWorkspaceId: id });
      },

      getActiveWorkspace: () => {
        const { workspaces, activeWorkspaceId } = get();
        return workspaces.find(w => w.id === activeWorkspaceId);
      }
    }),
    {
      name: 'workspace-storage',
      partialize: (state) => ({ activeWorkspaceId: state.activeWorkspaceId })
    }
  )
);
