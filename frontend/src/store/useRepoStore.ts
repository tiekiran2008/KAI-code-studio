import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Repository, FileNode } from '../types';
import { repositoriesApi } from '../api/repositories';

interface RepoState {
  repositories: Repository[];
  activeRepo: Repository | null;
  fileTree: FileNode[];
  selectedFile: FileNode | null;
  openTabs: FileNode[];
  searchQuery: string;
  isLoadingTree: boolean;
  treeError: string | null;
  isLoadingContent: boolean;
  contentError: string | null;

  setActiveRepo: (repo: Repository | null) => Promise<void>;
  loadFileTree: (repoId?: string) => Promise<void>;
  selectFile: (file: FileNode | null) => Promise<void>;
  openTab: (file: FileNode) => void;
  closeTab: (fileId: string) => void;
  setSearchQuery: (query: string) => void;
  setRepositories: (repos: Repository[]) => void;
  setSelectedBranch: (branch: string) => void;
  clearWorkspace: () => void;
}

export const useRepoStore = create<RepoState>()(
  persist(
    (set, get) => ({
      repositories: [],
      activeRepo: null,
      fileTree: [],
      selectedFile: null,
      openTabs: [],
      searchQuery: '',
      isLoadingTree: false,
      treeError: null,
      isLoadingContent: false,
      contentError: null,

      setActiveRepo: async (repo) => {
        set({
          activeRepo: repo,
          fileTree: [],
          selectedFile: null,
          openTabs: [],
          treeError: null,
          contentError: null,
        });
        if (repo) {
          await get().loadFileTree(repo.id);
        }
      },

      loadFileTree: async (repoId) => {
        const targetId = repoId || get().activeRepo?.id;
        if (!targetId) {
          set({ fileTree: [], isLoadingTree: false });
          return;
        }

        set({ isLoadingTree: true, treeError: null });
        try {
          const tree = await repositoriesApi.getFileTree(targetId);
          set({ fileTree: tree, isLoadingTree: false });
        } catch (err: any) {
          set({
            treeError: err.message || 'Failed to load repository files',
            isLoadingTree: false,
            fileTree: [],
          });
        }
      },

      selectFile: async (file) => {
        if (!file) {
          set({ selectedFile: null });
          return;
        }

        if (file.type === 'directory') {
          return;
        }

        const activeRepo = get().activeRepo;
        if (!activeRepo) return;

        // Open tab immediately with whatever info we have
        get().openTab(file);

        // If file already has content, just set selected
        if (file.content !== undefined) {
          set({ selectedFile: file });
          return;
        }

        set({ isLoadingContent: true, contentError: null, selectedFile: file });
        try {
          const res = await repositoriesApi.getFileContent(activeRepo.id, file.path);
          const fileWithContent: FileNode = {
            ...file,
            content: res.content,
            language: res.language || file.language,
            size: res.size,
          };

          // Update openTabs and selectedFile with loaded content
          const updatedTabs = get().openTabs.map((t) =>
            t.id === file.id ? fileWithContent : t
          );

          set({
            selectedFile: fileWithContent,
            openTabs: updatedTabs,
            isLoadingContent: false,
          });
        } catch (err: any) {
          const fallbackFile: FileNode = {
            ...file,
            content: `// Error loading file content: ${err.message || 'Unknown error'}`,
          };
          set({
            selectedFile: fallbackFile,
            contentError: err.message || 'Failed to load file content',
            isLoadingContent: false,
          });
        }
      },

      openTab: (file) => {
        if (file.type !== 'file') return;
        const { openTabs } = get();
        const existing = openTabs.find((t) => t.id === file.id);
        if (!existing) {
          set({ openTabs: [...openTabs, file], selectedFile: file });
        } else {
          set({ selectedFile: existing });
        }
      },

      closeTab: (fileId) => {
        const { openTabs, selectedFile } = get();
        const updatedTabs = openTabs.filter((t) => t.id !== fileId);
        let nextSelected = selectedFile;
        if (selectedFile?.id === fileId) {
          nextSelected = updatedTabs.length > 0 ? updatedTabs[updatedTabs.length - 1] : null;
        }
        set({ openTabs: updatedTabs, selectedFile: nextSelected });
      },

      setSearchQuery: (query) => set({ searchQuery: query }),
      setRepositories: (repos) => set({ repositories: repos }),

      setSelectedBranch: (branch) => {
        const { activeRepo } = get();
        if (activeRepo) {
          set({ activeRepo: { ...activeRepo, currentBranch: branch, current_branch: branch } });
        }
      },

      clearWorkspace: () => {
        set({
          activeRepo: null,
          fileTree: [],
          selectedFile: null,
          openTabs: [],
          treeError: null,
          contentError: null,
        });
      },
    }),
    {
      name: 'ai-workspace-repo-storage',
      partialize: (state) => ({
        activeRepo: state.activeRepo,
      }),
    }
  )
);
