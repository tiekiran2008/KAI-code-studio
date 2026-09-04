import { create } from 'zustand';
import { ConversationSession, ChatMessage } from '../types';
import { MOCK_SESSIONS } from '../api/mockData';
import { api } from '../api/client';

interface ChatState {
  sessions: ConversationSession[];
  activeSessionId: string;
  isGenerating: boolean;
  activeSession: () => ConversationSession | undefined;
  setActiveSessionId: (id: string) => void;
  sendMessage: (content: string, repoId?: string) => Promise<void>;
  createSession: () => void;
  clearSessionMessages: (id: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: MOCK_SESSIONS,
  activeSessionId: MOCK_SESSIONS[0].id,
  isGenerating: false,

  activeSession: () => {
    const { sessions, activeSessionId } = get();
    return sessions.find((s) => s.id === activeSessionId) || sessions[0];
  },

  setActiveSessionId: (id) => set({ activeSessionId: id }),

  sendMessage: async (content, repoId) => {
    const session = get().activeSession();
    if (!session) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    // Append user message immediately
    const updatedMessages = [...session.messages, userMsg];
    set((state) => ({
      isGenerating: true,
      sessions: state.sessions.map((s) =>
        s.id === session.id ? { ...s, messages: updatedMessages, updatedAt: new Date().toISOString() } : s
      ),
    }));

    try {
      // Execute multi-agent backend call or mock simulation
      const result = await api.executeAgentWorkflow(content, repoId || 'repo-1');

      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: result.final_answer || 'Response completed.',
        timestamp: new Date().toISOString(),
        agentTraces: result.execution_trace || [],
        citations: result.citations || [
          {
            file_path: 'backend/src/application/agents/supervisor.py',
            start_line: 14,
            end_line: 45,
            snippet: 'class SupervisorAgent:\n    async def execute(self, state):'
          }
        ],
        toolCalls: [
          {
            tool_name: 'local_fs_read',
            caller_agent: 'SupervisorAgent',
            arguments: { action: 'read_file', path: 'backend/src/application/agents/supervisor.py' },
            success: true,
            latency_ms: 18.5,
            timestamp: new Date().toISOString()
          }
        ]
      };

      set((state) => ({
        isGenerating: false,
        sessions: state.sessions.map((s) =>
          s.id === session.id
            ? { ...s, messages: [...updatedMessages, assistantMsg], updatedAt: new Date().toISOString() }
            : s
        ),
      }));
    } catch {
      set({ isGenerating: false });
    }
  },

  createSession: () => {
    const newSession: ConversationSession = {
      id: `session-${Date.now()}`,
      title: 'New AI Architecture Session',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    };
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      activeSessionId: newSession.id,
    }));
  },

  clearSessionMessages: (id) => {
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? { ...s, messages: [] } : s)),
    }));
  },
}));
