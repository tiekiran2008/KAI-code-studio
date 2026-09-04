import { create } from 'zustand';
import { Repository, FileNode } from '../types';
import { MOCK_REPOSITORIES, MOCK_FILE_TREE } from '../api/mockData';

interface RepoState {
  repositories: Repository[];
  activeRepo: Repository | null;
  fileTree: FileNode[];
  selectedFile: FileNode | null;
  openTabs: FileNode[];
  searchQuery: string;
  setActiveRepo: (repo: Repository) => void;
  setSelectedFile: (file: FileNode | null) => void;
  openTab: (file: FileNode) => void;
  closeTab: (fileId: string) => void;
  setSearchQuery: (query: string) => void;
  setRepositories: (repos: Repository[]) => void;
  setSelectedBranch: (branch: string) => void;
}

export const useRepoStore = create<RepoState>((set, get) => ({
  repositories: MOCK_REPOSITORIES,
  activeRepo: MOCK_REPOSITORIES[0],
  fileTree: MOCK_FILE_TREE,
  selectedFile: MOCK_FILE_TREE[0].children?.[0].children?.[0] || null, // backend/src/main.py
  openTabs: [MOCK_FILE_TREE[0].children?.[0].children?.[0]].filter(Boolean) as FileNode[],
  searchQuery: '',

  setActiveRepo: (repo) => set({ activeRepo: repo }),
  
  setSelectedFile: (file) => {
    if (!file) {
      set({ selectedFile: null });
      return;
    }
    set({ selectedFile: file });
    if (file.type === 'file') {
      get().openTab(file);
    }
  },

  openTab: (file) => {
    if (file.type !== 'file') return;
    const { openTabs } = get();
    if (!openTabs.some((t) => t.id === file.id)) {
      set({ openTabs: [...openTabs, file], selectedFile: file });
    } else {
      set({ selectedFile: file });
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
      set({ activeRepo: { ...activeRepo, currentBranch: branch } });
    }
  }
}));
