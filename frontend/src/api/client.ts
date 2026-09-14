import { 
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
  ConversationSession,
  ChatMessage 
} from '../types';
import { fetchClient } from './fetchClient';

function mapMemoryResponse(m: any): MemoryRecord {
  return {
    id: m.id,
    userId: m.user_id || 'usr-admin-1',
    repositoryId: m.repository_id || undefined,
    memoryType: m.memory_type || 'long_term',
    content: m.content || m.summary || '',
    importanceScore: m.score?.importance ?? 0.8,
    createdAt: m.created_at || new Date().toISOString(),
    updatedAt: m.created_at || new Date().toISOString(),
    techStack: m.score?.tags || [],
    isEncrypted: m.metadata?.encrypted ?? false,
  };
}

export const api = {
  // Repositories
  getRepositories: async (): Promise<Repository[]> => {
    return fetchClient.get<Repository[]>('/repositories');
  },

  importRepository: async (url: string, branch: string): Promise<Repository> => {
    return fetchClient.post<Repository>('/repositories/import', {
      url,
      default_branch: branch || 'main',
    });
  },

  uploadLocalRepository: async (name: string, file?: File): Promise<Repository> => {
    const formData = new FormData();
    formData.append('name', name);
    if (file) formData.append('file', file);
    return fetchClient.post<Repository>('/repositories/upload', formData);
  },

  deleteRepository: async (repoId: string): Promise<boolean> => {
    await fetchClient.delete(`/repositories/${repoId}`);
    return true;
  },

  reindexRepository: async (repoId: string): Promise<Repository | null> => {
    return fetchClient.post<Repository>(`/repositories/${repoId}/reindex`);
  },

  // File Tree & Content
  getFileTree: async (repoId: string): Promise<FileNode[]> => {
    return fetchClient.get<FileNode[]>(`/repositories/${repoId}/tree`);
  },

  getFileContent: async (repoId: string, path: string): Promise<any> => {
    return fetchClient.get<any>(`/repositories/${repoId}/files/content`, {
      params: { path },
    });
  },


  // Memories
  getMemories: async (_userId: string = 'usr-admin-1'): Promise<MemoryRecord[]> => {
    try {
      const res = await fetchClient.get<{ memories: any[] }>('/memory');
      return (res.memories || []).map(mapMemoryResponse);
    } catch (e) {
      console.warn('Failed to fetch memories from backend:', e);
      return MOCK_MEMORIES;
    }
  },

  searchMemories: async (query: string, _userId: string = 'usr-admin-1'): Promise<MemoryRecord[]> => {
    if (!query.trim()) {
      return api.getMemories(_userId);
    }
    try {
      const res = await fetchClient.post<{ results: { memory: any }[] }>('/memory/search', {
        query,
      });
      return (res.results || []).map(r => mapMemoryResponse(r.memory));
    } catch (e) {
      console.warn('Memory search backend call failed, filtering locally:', e);
      const lower = query.toLowerCase();
      return MOCK_MEMORIES.filter(m => m.content.toLowerCase().includes(lower) || m.memoryType.includes(lower));
    }
  },

  deleteMemory: async (memoryId: string): Promise<boolean> => {
    await fetchClient.delete(`/memory/${memoryId}`);
    return true;
  },

  // Tools
  getRegisteredTools: async (): Promise<ToolMetadata[]> => {
    try {
      return await fetchClient.get<ToolMetadata[]>('/tools');
    } catch {
      return MOCK_TOOLS;
    }
  },

  // Analytics & Health (Simulated / Preview Platform Metrics)
  getAnalytics: async (): Promise<AnalyticsMetrics> => {
    return MOCK_ANALYTICS;
  },

  // Sessions & Conversations
  getSessions: async (repoId?: string): Promise<ConversationSession[]> => {
    try {
      const params = repoId ? { repository_id: repoId } : undefined;
      const res = await fetchClient.get<any[]>('/conversations', { params });
      return res.map(s => ({
        id: s.id,
        title: s.title,
        repositoryId: s.repositoryId || s.repository_id,
        createdAt: s.createdAt || s.created_at,
        updatedAt: s.updatedAt || s.updated_at,
        messages: [],
      }));
    } catch (e) {
      console.warn('Failed to fetch conversation sessions:', e);
      return [];
    }
  },

  getConversation: async (sessionId: string): Promise<ConversationSession | null> => {
    try {
      const res = await fetchClient.get<any>(`/conversations/${sessionId}`);
      return {
        id: res.id,
        title: res.title,
        repositoryId: res.repositoryId || res.repository_id,
        createdAt: res.createdAt || res.created_at,
        updatedAt: res.updatedAt || res.updated_at,
        messages: (res.messages || []).map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || m.created_at || new Date().toISOString(),
          agentTraces: m.agentTraces || m.agent_traces || [],
          citations: m.citations || [],
          toolCalls: m.toolCalls || m.tool_calls || [],
        })),
      };
    } catch (e) {
      console.warn(`Failed to fetch conversation ${sessionId}:`, e);
      return null;
    }
  },

  createConversation: async (data: { id?: string; title?: string; repository_id?: string }): Promise<ConversationSession> => {
    const res = await fetchClient.post<any>('/conversations', data);
    return {
      id: res.id,
      title: res.title,
      repositoryId: res.repositoryId || res.repository_id,
      createdAt: res.createdAt || res.created_at,
      updatedAt: res.updatedAt || res.updated_at,
      messages: res.messages || [],
    };
  },

  deleteConversation: async (sessionId: string): Promise<boolean> => {
    try {
      await fetchClient.delete(`/conversations/${sessionId}`);
      return true;
    } catch (e) {
      console.warn(`Failed to delete conversation ${sessionId}:`, e);
      return false;
    }
  },

  saveChatMessage: async (
    sessionId: string,
    message: {
      id?: string;
      role: 'user' | 'assistant' | 'system';
      content: string;
      agentTraces?: any[];
      citations?: any[];
      toolCalls?: any[];
    }
  ): Promise<ChatMessage> => {
    const res = await fetchClient.post<any>(`/conversations/${sessionId}/messages`, {
      id: message.id,
      role: message.role,
      content: message.content,
      agentTraces: message.agentTraces,
      citations: message.citations,
      toolCalls: message.toolCalls,
    });
    return {
      id: res.id,
      role: res.role,
      content: res.content,
      timestamp: res.timestamp || res.created_at || new Date().toISOString(),
      agentTraces: res.agentTraces || [],
      citations: res.citations || [],
      toolCalls: res.toolCalls || [],
    };
  },

  clearConversationMessages: async (sessionId: string): Promise<boolean> => {
    try {
      await fetchClient.delete(`/conversations/${sessionId}/messages`);
      return true;
    } catch (e) {
      console.warn(`Failed to clear messages for conversation ${sessionId}:`, e);
      return false;
    }
  },

  executeAgentWorkflow: async (query: string, repoId: string, sessionId?: string): Promise<any> => {
    try {
      const res = await fetchClient.post<any>('/agents/execute', {
        query,
        repo_id: repoId,
        session_id: sessionId,
      });
      return {
        final_answer: res.answer || res.final_answer || '',
        execution_trace: res.execution_trace || [],
        citations: res.citations || [],
        plan: res.plan,
        agent_outputs: res.agent_outputs,
        confidence_score: res.confidence_score,
      };
    } catch (e) {
      console.warn('Agent execution API call failed:', e);
      throw e;
    }
  }
};

