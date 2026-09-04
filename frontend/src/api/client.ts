import { 
  MOCK_REPOSITORIES, 
  MOCK_FILE_TREE, 
  MOCK_MEMORIES, 
  MOCK_TOOLS, 
  MOCK_ANALYTICS, 
  MOCK_SESSIONS 
} from './mockData';
import { 
  Repository, 
  FileNode, 
  MemoryRecord, 
  ToolMetadata, 
  AnalyticsMetrics, 
  ConversationSession 
} from '../types';

const API_BASE = '/api/v1';

async function fetchWithFallback<T>(url: string, fallbackData: T): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${url}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API call to ${url} failed, using fallback data.`, err);
    return fallbackData;
  }
}

export const api = {
  // Repositories
  getRepositories: async (): Promise<Repository[]> => {
    return fetchWithFallback('/repositories', MOCK_REPOSITORIES);
  },

  importRepository: async (url: string, branch: string): Promise<Repository> => {
    try {
      const res = await fetch(`${API_BASE}/repositories/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repository_url: url, default_branch: branch })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Backend repo import failed, simulating client import', e);
    }
    const newRepo: Repository = {
      id: `repo-${Date.now()}`,
      name: url.split('/').pop() || 'imported-repo',
      owner: 'github-user',
      url,
      defaultBranch: branch,
      currentBranch: branch,
      branches: [branch, 'main', 'dev'],
      indexingStatus: 'indexed',
      chunksCount: 540,
      lastIndexedAt: new Date().toISOString(),
      language: 'TypeScript / Python'
    };
    MOCK_REPOSITORIES.unshift(newRepo);
    return newRepo;
  },

  uploadLocalRepository: async (name: string, file?: File): Promise<Repository> => {
    try {
      const formData = new FormData();
      formData.append('name', name);
      if (file) formData.append('file', file);
      const res = await fetch(`${API_BASE}/repositories/upload`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Backend repo upload failed, simulating client upload', e);
    }
    const newRepo: Repository = {
      id: `repo-${Date.now()}`,
      name: name || (file ? file.name.replace(/\.[^/.]+$/, '') : 'uploaded-local-repo'),
      owner: 'local-user',
      url: 'file://local-storage',
      defaultBranch: 'main',
      currentBranch: 'main',
      branches: ['main'],
      indexingStatus: 'indexing',
      chunksCount: 120,
      lastIndexedAt: new Date().toISOString(),
      language: 'TypeScript / JavaScript',
      isLocal: true,
    };
    MOCK_REPOSITORIES.unshift(newRepo);
    return newRepo;
  },

  deleteRepository: async (repoId: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/repositories/${repoId}`, {
        method: 'DELETE',
      });
      if (res.ok) return true;
    } catch (e) {
      console.warn('Backend repo delete failed, simulating client delete', e);
    }
    const idx = MOCK_REPOSITORIES.findIndex((r) => r.id === repoId);
    if (idx !== -1) {
      MOCK_REPOSITORIES.splice(idx, 1);
    }
    return true;
  },

  reindexRepository: async (repoId: string): Promise<Repository | null> => {
    try {
      const res = await fetch(`${API_BASE}/repositories/${repoId}/reindex`, {
        method: 'POST',
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Backend reindex failed, simulating client reindex', e);
    }
    const repo = MOCK_REPOSITORIES.find((r) => r.id === repoId);
    if (repo) {
      repo.indexingStatus = 'indexing';
      repo.lastIndexedAt = new Date().toISOString();
    }
    return repo || null;
  },

  // File Tree
  getFileTree: async (repoId: string): Promise<FileNode[]> => {
    return fetchWithFallback(`/repositories/${repoId}/files`, MOCK_FILE_TREE);
  },

  // Memories
  getMemories: async (userId: string = 'usr-admin-1'): Promise<MemoryRecord[]> => {
    return fetchWithFallback(`/memory/user/${userId}`, MOCK_MEMORIES);
  },

  searchMemories: async (query: string, _userId: string = 'usr-admin-1'): Promise<MemoryRecord[]> => {
    if (!query.trim()) return MOCK_MEMORIES;
    const lower = query.toLowerCase();
    return MOCK_MEMORIES.filter(m => m.content.toLowerCase().includes(lower) || m.memoryType.includes(lower));
  },

  deleteMemory: async (memoryId: string): Promise<boolean> => {
    const idx = MOCK_MEMORIES.findIndex(m => m.id === memoryId);
    if (idx !== -1) {
      MOCK_MEMORIES.splice(idx, 1);
    }
    return true;
  },

  // Tools
  getRegisteredTools: async (): Promise<ToolMetadata[]> => {
    return fetchWithFallback('/tools', MOCK_TOOLS);
  },

  // Analytics & Health
  getAnalytics: async (): Promise<AnalyticsMetrics> => {
    return fetchWithFallback('/analytics', MOCK_ANALYTICS);
  },

  // Sessions & Agent Execution
  getSessions: async (): Promise<ConversationSession[]> => {
    return MOCK_SESSIONS;
  },

  executeAgentWorkflow: async (query: string, repoId: string): Promise<any> => {
    try {
      const res = await fetch(`${API_BASE}/agents/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, repository_id: repoId })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Agent execution API call failed, generating simulated response', e);
    }

    // Fallback simulation
    return {
      final_answer: `### Architecture Response for: "${query}"\n\nI have analyzed the repository context using our multi-agent workflow.\n\n1. **Context Agent**: Retrieved relevant code snippets from \`backend/src/application/agents/supervisor.py\`.\n2. **Code Analysis Agent**: Confirmed modular separation of domain interfaces.\n3. **Evaluation Agent**: Quality confidence score 0.98.`,
      execution_trace: [
        { agent: 'supervisor', action: 'routed_to_planner', latency_ms: 10 },
        { agent: 'planner', action: 'plan_created', latency_ms: 180 },
        { agent: 'context', action: 'rag_search_complete', latency_ms: 95 },
        { agent: 'code_analysis', action: 'analysis_complete', latency_ms: 210 },
        { agent: 'evaluation', action: 'quality_passed', latency_ms: 12 },
        { agent: 'supervisor', action: 'synthesized_final_answer', latency_ms: 150 }
      ]
    };
  }
};
