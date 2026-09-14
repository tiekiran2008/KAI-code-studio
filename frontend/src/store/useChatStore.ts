import { create } from 'zustand';
import { ConversationSession, ChatMessage } from '../types';
import { api } from '../api/client';

interface ChatState {
  sessions: ConversationSession[];
  activeSessionId: string;
  isGenerating: boolean;
  isLoadingHistory: boolean;
  activeSession: () => ConversationSession | undefined;
  setActiveSessionId: (id: string) => void;
  loadSessions: (repoId?: string) => Promise<void>;
  selectSession: (id: string) => Promise<void>;
  createSession: (repoId?: string, title?: string) => Promise<ConversationSession>;
  deleteSession: (id: string) => Promise<void>;
  clearSessionMessages: (id: string) => Promise<void>;
  sendMessage: (content: string, repoId?: string, filePath?: string) => Promise<void>;
  stopGeneration: () => void;
}

const createInitialSession = (repoId?: string, title?: string): ConversationSession => ({
  id: `session-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
  title: title || 'AI Engineering Session',
  repositoryId: repoId,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  messages: [],
});

const defaultSession = createInitialSession();

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [defaultSession],
  activeSessionId: defaultSession.id,
  isGenerating: false,
  isLoadingHistory: false,

  activeSession: () => {
    const { sessions, activeSessionId } = get();
    return sessions.find((s) => s.id === activeSessionId) || sessions[0];
  },

  setActiveSessionId: (id) => set({ activeSessionId: id }),

  loadSessions: async (repoId?: string) => {
    set({ isLoadingHistory: true });
    try {
      const backendSessions = await api.getSessions(repoId);
      if (backendSessions && backendSessions.length > 0) {
        // Find if current active session exists in backend
        const currentActive = get().activeSessionId;
        const targetId = backendSessions.some((s) => s.id === currentActive)
          ? currentActive
          : backendSessions[0].id;

        // Fetch full details (messages) for the target active session
        const activeDetail = await api.getConversation(targetId);

        const populatedSessions = backendSessions.map((s) => {
          if (activeDetail && s.id === activeDetail.id) {
            return activeDetail;
          }
          return { ...s, messages: s.messages || [] };
        });

        set({
          sessions: populatedSessions,
          activeSessionId: targetId,
          isLoadingHistory: false,
        });
      } else {
        // No sessions exist yet in database — create initial session on backend
        const initial = createInitialSession(repoId);
        try {
          const created = await api.createConversation({
            id: initial.id,
            title: initial.title,
            repository_id: repoId,
          });
          set({
            sessions: [{ ...created, messages: [] }],
            activeSessionId: created.id,
            isLoadingHistory: false,
          });
        } catch {
          set({
            sessions: [initial],
            activeSessionId: initial.id,
            isLoadingHistory: false,
          });
        }
      }
    } catch (err) {
      console.warn('Failed to load chat history:', err);
      set({ isLoadingHistory: false });
    }
  },

  selectSession: async (id: string) => {
    set({ activeSessionId: id });
    const existing = get().sessions.find((s) => s.id === id);
    if (!existing || !existing.messages || existing.messages.length === 0) {
      set({ isLoadingHistory: true });
      try {
        const detail = await api.getConversation(id);
        if (detail) {
          set((state) => ({
            sessions: state.sessions.map((s) => (s.id === id ? detail : s)),
            isLoadingHistory: false,
          }));
        } else {
          set({ isLoadingHistory: false });
        }
      } catch {
        set({ isLoadingHistory: false });
      }
    }
  },

  createSession: async (repoId?: string, title?: string) => {
    const newSession = createInitialSession(repoId, title);
    try {
      const created = await api.createConversation({
        id: newSession.id,
        title: newSession.title,
        repository_id: repoId,
      });
      const sessionWithMsgs: ConversationSession = { ...created, messages: [] };
      set((state) => ({
        sessions: [sessionWithMsgs, ...state.sessions.filter((s) => s.id !== sessionWithMsgs.id)],
        activeSessionId: sessionWithMsgs.id,
      }));
      return sessionWithMsgs;
    } catch (err) {
      console.warn('Failed to persist new session in backend:', err);
      set((state) => ({
        sessions: [newSession, ...state.sessions],
        activeSessionId: newSession.id,
      }));
      return newSession;
    }
  },

  deleteSession: async (id: string) => {
    await api.deleteConversation(id);
    set((state) => {
      const remaining = state.sessions.filter((s) => s.id !== id);
      const nextActive = remaining.length > 0 ? remaining[0].id : '';
      return {
        sessions: remaining.length > 0 ? remaining : [createInitialSession()],
        activeSessionId: nextActive || (remaining[0]?.id ?? ''),
      };
    });
  },

  clearSessionMessages: async (id: string) => {
    await api.clearConversationMessages(id);
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? { ...s, messages: [] } : s)),
    }));
  },

  sendMessage: async (content: string, repoId?: string, filePath?: string) => {
    let session = get().activeSession();
    if (!session) {
      session = await get().createSession(repoId);
    }

    const userMsgId = `msg-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    // Append user message immediately to local state so user sees it
    const updatedMessages = [...session.messages, userMsg];
    const newTitle = session.title === 'AI Engineering Session' && content ? content.slice(0, 45).trim() : session.title;
    
    set((state) => ({
      isGenerating: true,
      sessions: state.sessions.map((s) =>
        s.id === session!.id
          ? { ...s, title: newTitle, messages: updatedMessages, updatedAt: new Date().toISOString() }
          : s
      ),
    }));

    // Persist user message to PostgreSQL database immediately
    try {
      await api.saveChatMessage(session.id, {
        id: userMsgId,
        role: 'user',
        content,
      });
    } catch (err) {
      console.warn('Could not persist user chat message to backend:', err);
    }

    try {
      // Build effective query with file context if available
      let effectiveQuery = content;
      if (filePath && !content.toLowerCase().includes(filePath.toLowerCase())) {
        effectiveQuery = `[Context File: ${filePath}]\n${content}`;
      }

      const result = await api.executeAgentWorkflow(effectiveQuery, repoId || '', session.id);

      const assistantMsgId = `msg-${Date.now() + 1}-${Math.random().toString(36).substring(2, 6)}`;
      const assistantMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: result.final_answer || 'Response completed.',
        timestamp: new Date().toISOString(),
        agentTraces: result.execution_trace || [],
        citations: result.citations || [],
        toolCalls: result.tool_calls || [],
      };

      set((state) => ({
        isGenerating: false,
        sessions: state.sessions.map((s) =>
          s.id === session!.id
            ? { ...s, messages: [...updatedMessages, assistantMsg], updatedAt: new Date().toISOString() }
            : s
        ),
      }));

      // Persist assistant message to PostgreSQL database
      try {
        await api.saveChatMessage(session.id, {
          id: assistantMsgId,
          role: 'assistant',
          content: assistantMsg.content,
          agentTraces: assistantMsg.agentTraces,
          citations: assistantMsg.citations,
          toolCalls: assistantMsg.toolCalls,
        });
      } catch (err) {
        console.warn('Could not persist assistant chat message to backend:', err);
      }
    } catch (err: any) {
      const errorMsgId = `msg-${Date.now() + 1}-${Math.random().toString(36).substring(2, 6)}`;
      const errorMsg: ChatMessage = {
        id: errorMsgId,
        role: 'assistant',
        content: `Error executing AI agent: ${err.message || 'Unable to connect to AI Co-Pilot backend.'}`,
        timestamp: new Date().toISOString(),
      };
      set((state) => ({
        isGenerating: false,
        sessions: state.sessions.map((s) =>
          s.id === session!.id
            ? { ...s, messages: [...updatedMessages, errorMsg], updatedAt: new Date().toISOString() }
            : s
        ),
      }));

      try {
        await api.saveChatMessage(session.id, {
          id: errorMsgId,
          role: 'assistant',
          content: errorMsg.content,
        });
      } catch (saveErr) {
        console.warn('Could not persist error message to backend:', saveErr);
      }
    }
  },

  stopGeneration: () => {
    const session = get().activeSession();
    if (!session) {
      set({ isGenerating: false });
      return;
    }
    const stoppedMsgId = `msg-${Date.now()}`;
    const stoppedMsg: ChatMessage = {
      id: stoppedMsgId,
      role: 'assistant',
      content: '*(Execution stopped by user)*',
      timestamp: new Date().toISOString(),
    };
    set((state) => ({
      isGenerating: false,
      sessions: state.sessions.map((s) =>
        s.id === session.id
          ? { ...s, messages: [...s.messages, stoppedMsg], updatedAt: new Date().toISOString() }
          : s
      ),
    }));

    api.saveChatMessage(session.id, {
      id: stoppedMsgId,
      role: 'assistant',
      content: stoppedMsg.content,
    }).catch(() => {});
  },
}));
