import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Sparkles,
  Send,
  Cpu,
  ChevronRight,
  Wrench,
  BookOpen,
  ExternalLink,
  User,
  Bot,
  RefreshCw,
  Plus,
  Trash2,
  MessageSquare,
  StopCircle,
  ChevronDown,
} from 'lucide-react';
import { ConversationSession, Citation } from '../../types';
import { useChatStore } from '../../store/useChatStore';

interface AIChatPanelProps {
  session: ConversationSession | undefined;
  activeRepoId?: string;
  activeFilePath?: string;
  onSelectCitation: (citation: Citation) => void;
}

// ---------------------------------------------------------------------------
// Markdown component renderers — styled for the dark glass theme
// ---------------------------------------------------------------------------
const markdownComponents = {
  h1: ({ children }: any) => (
    <h1 className="text-sm font-bold text-white mt-3 mb-1.5 border-b border-slate-700 pb-1">{children}</h1>
  ),
  h2: ({ children }: any) => (
    <h2 className="text-xs font-bold text-indigo-300 mt-2.5 mb-1">{children}</h2>
  ),
  h3: ({ children }: any) => (
    <h3 className="text-xs font-semibold text-slate-200 mt-2 mb-1">{children}</h3>
  ),
  p: ({ children }: any) => (
    <p className="text-xs leading-relaxed text-slate-200 mb-2 last:mb-0">{children}</p>
  ),
  ul: ({ children }: any) => (
    <ul className="list-disc list-inside space-y-0.5 mb-2 pl-1 text-xs text-slate-300">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="list-decimal list-inside space-y-0.5 mb-2 pl-1 text-xs text-slate-300">{children}</ol>
  ),
  li: ({ children }: any) => (
    <li className="text-xs text-slate-300 leading-relaxed">{children}</li>
  ),
  code: ({ inline, children }: any) =>
    inline ? (
      <code className="px-1 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-[11px] border border-slate-700">
        {children}
      </code>
    ) : (
      <code className="block bg-slate-950 border border-slate-700 rounded-lg p-3 font-mono text-[11px] text-cyan-200 overflow-x-auto whitespace-pre my-2 leading-relaxed">
        {children}
      </code>
    ),
  pre: ({ children }: any) => <>{children}</>,
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-2 border-indigo-500 pl-3 my-2 text-slate-400 italic text-xs">
      {children}
    </blockquote>
  ),
  table: ({ children }: any) => (
    <div className="overflow-x-auto my-2">
      <table className="w-full text-[11px] border-collapse border border-slate-700 rounded">{children}</table>
    </div>
  ),
  thead: ({ children }: any) => <thead className="bg-slate-800">{children}</thead>,
  tbody: ({ children }: any) => <tbody>{children}</tbody>,
  tr: ({ children }: any) => <tr className="border-b border-slate-800">{children}</tr>,
  th: ({ children }: any) => (
    <th className="px-2 py-1 text-left text-slate-200 font-semibold border-r border-slate-700 last:border-r-0">
      {children}
    </th>
  ),
  td: ({ children }: any) => (
    <td className="px-2 py-1 text-slate-300 border-r border-slate-700 last:border-r-0">{children}</td>
  ),
  strong: ({ children }: any) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }: any) => <em className="italic text-slate-300">{children}</em>,
  hr: () => <hr className="border-slate-700 my-3" />,
  a: ({ href, children }: any) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export const AIChatPanel: React.FC<AIChatPanelProps> = ({
  session,
  activeRepoId,
  activeFilePath,
  onSelectCitation,
}) => {
  const {
    sessions,
    activeSessionId,
    selectSession,
    loadSessions,
    sendMessage,
    createSession,
    clearSessionMessages,
    deleteSession,
    stopGeneration,
    isGenerating,
    isLoadingHistory,
  } = useChatStore();

  const [inputQuery, setInputQuery] = useState('');
  const [expandedTraceMsgId, setExpandedTraceMsgId] = useState<string | null>(null);

  // Auto-scroll refs
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUp = useRef(false);
  const lastMessageCount = useRef(0);

  // Load conversation sessions from PostgreSQL backend on mount & repo change
  useEffect(() => {
    loadSessions(activeRepoId);
  }, [activeRepoId, loadSessions]);

  // ---------------------------------------------------------------------------
  // Smart auto-scroll logic
  // ---------------------------------------------------------------------------
  const scrollToBottom = useCallback((force = false) => {
    if (force || !isUserScrolledUp.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    // Pause auto-scroll when user is more than 80px from bottom
    isUserScrolledUp.current = distanceFromBottom > 80;
  }, []);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    const currentCount = session?.messages?.length ?? 0;
    if (currentCount !== lastMessageCount.current) {
      lastMessageCount.current = currentCount;
      scrollToBottom();
    }
  }, [session?.messages?.length, scrollToBottom]);

  // Scroll to bottom when generation starts
  useEffect(() => {
    if (isGenerating) {
      scrollToBottom();
    }
  }, [isGenerating, scrollToBottom]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isGenerating) return;
    const text = inputQuery;
    setInputQuery('');
    isUserScrolledUp.current = false; // Force scroll on new send
    await sendMessage(text, activeRepoId, activeFilePath);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e as any);
    }
  };

  const handleChipClick = (promptText: string) => {
    setInputQuery(activeFilePath ? `${promptText} for ${activeFilePath}` : promptText);
  };

  const handleScrollToBottom = () => {
    isUserScrolledUp.current = false;
    scrollToBottom(true);
  };

  // Row count for auto-resizing textarea
  const textareaRows = Math.min(Math.max(inputQuery.split('\n').length, 1), 4);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className={`w-full h-full glass-panel rounded-2xl flex flex-col overflow-hidden border border-slate-800 transition-all${isGenerating ? ' ambient-ai-generating' : ''}`}>

      {/* ── Header ── */}
      <div className="p-3 border-b border-slate-800 bg-slate-900/60 space-y-2 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span className="font-semibold text-xs text-white">AI Engineering Co-Pilot</span>
          </div>
          <button
            onClick={() => createSession(activeRepoId)}
            className="p-1 px-2 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs font-medium border border-indigo-500/30 flex items-center gap-1 transition-colors"
            title="Create new conversation session"
          >
            <Plus className="w-3 h-3" /> New Chat
          </button>
        </div>

        <div className="flex items-center gap-2">
          <MessageSquare className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <select
            value={activeSessionId}
            onChange={(e) => selectSession(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 text-[11px] text-slate-200 py-1 px-2 rounded-lg focus:outline-none focus:border-indigo-500 truncate"
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title || 'Untitled Session'}
              </option>
            ))}
          </select>
          {session && (
            <button
              onClick={() => clearSessionMessages(session.id)}
              className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
              title="Clear session messages"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* ── Messages ── */}
      <div
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 min-w-0 p-4 overflow-y-auto overflow-x-hidden space-y-4"
        style={{ overscrollBehavior: 'contain' }}
      >
        {/* Loading history state */}
        {isLoadingHistory && (
          <div className="flex items-center justify-center py-8 text-xs text-slate-400 font-mono gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
            <span>Loading conversation history…</span>
          </div>
        )}

        {/* Empty state */}
        {!isLoadingHistory && (session?.messages?.length ?? 0) === 0 && !isGenerating && (
          <div className="text-center py-8 space-y-2">
            <Bot className="w-8 h-8 text-indigo-400 mx-auto animate-bounce" />
            <p className="text-xs font-medium text-slate-300">How can I assist your engineering work?</p>
            <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
              Ask about codebase architecture, security vulnerabilities, or unit test generation.
            </p>
          </div>
        )}

        {/* Message list */}
        {session?.messages?.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col gap-1.5 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            {/* Role label */}
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
              {msg.role === 'user' ? (
                <><span>You</span><User className="w-3 h-3 text-indigo-400" /></>
              ) : (
                <><Bot className="w-3 h-3 text-cyan-400" /><span>KAI Co-Pilot</span></>
              )}
            </div>

            {/* Bubble */}
            <div
              className={`rounded-2xl leading-relaxed max-w-[95%] shadow-lg break-words min-w-0 overflow-hidden ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-none px-3.5 py-2.5 text-xs'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none px-3.5 py-3 space-y-1'
              }`}
            >
              {msg.role === 'user' ? (
                <div className="whitespace-pre-wrap break-words text-xs">{msg.content}</div>
              ) : (
                <div className="break-words min-w-0 overflow-hidden text-xs">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}

              {/* Agent Traces */}
              {msg.agentTraces && msg.agentTraces.length > 0 && (
                <div className="pt-2 border-t border-slate-800/80 mt-2">
                  <button
                    onClick={() => setExpandedTraceMsgId(expandedTraceMsgId === msg.id ? null : msg.id)}
                    className="flex items-center justify-between w-full text-[10px] text-indigo-400 font-mono hover:underline"
                  >
                    <span className="flex items-center gap-1">
                      <Cpu className="w-3 h-3" /> Agent Trace ({msg.agentTraces.length} steps)
                    </span>
                    <ChevronRight
                      className={`w-3 h-3 transition-transform ${expandedTraceMsgId === msg.id ? 'rotate-90' : ''}`}
                    />
                  </button>
                  {expandedTraceMsgId === msg.id && (
                    <div className="mt-2 space-y-1 pl-2 border-l border-indigo-500/30 text-[10px] font-mono">
                      {msg.agentTraces.map((t, idx) => (
                        <div key={idx} className="flex items-center justify-between text-slate-400">
                          <span className="text-indigo-300 font-semibold">{t.agent.toUpperCase()}</span>
                          <span>{t.action}</span>
                          <span className="text-slate-500">{t.latency_ms}ms</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tool Calls */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {msg.toolCalls.map((tc, i) => (
                    <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-slate-700">
                      <Wrench className="w-2.5 h-2.5 text-amber-400" />
                      {tc.tool_name} ({tc.latency_ms}ms)
                    </span>
                  ))}
                </div>
              )}

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="pt-2 border-t border-slate-800/60 space-y-1 mt-2">
                  <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                    <BookOpen className="w-3 h-3 text-cyan-400" /> Source References:
                  </div>
                  {msg.citations.map((c, i) => (
                    <div
                      key={i}
                      onClick={() => onSelectCitation(c)}
                      className="p-1.5 rounded bg-slate-950 hover:bg-slate-800 text-[10px] font-mono text-cyan-300 border border-slate-800 flex items-center justify-between cursor-pointer transition-colors"
                    >
                      <span className="truncate">{c.file_path}#L{c.start_line}-{c.end_line}</span>
                      <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Generation Status Bar ── */}
      {isGenerating && (
        <div className="px-3 py-2 border-t border-slate-800/60 bg-slate-950/70 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-[11px] text-indigo-300 font-mono animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
            <span>Multi-Agent Reasoning…</span>
          </div>
          <button
            onClick={stopGeneration}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-950/50 hover:bg-rose-900/70 border border-rose-800/50 text-rose-400 text-[11px] font-medium transition-all"
          >
            <StopCircle className="w-3 h-3" /> Stop
          </button>
        </div>
      )}

      {/* ── Action Chips + Scroll Button ── */}
      <div className="px-2 py-1.5 border-t border-slate-800/80 bg-slate-950/40 flex gap-1.5 overflow-x-auto shrink-0">
        <button
          onClick={() => handleChipClick('Explain function architecture in open file.')}
          disabled={isGenerating}
          className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] whitespace-nowrap transition-colors disabled:opacity-50"
        >
          Explain Architecture
        </button>
        <button
          onClick={() => handleChipClick('Check open file for security OWASP vulnerabilities.')}
          disabled={isGenerating}
          className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] whitespace-nowrap transition-colors disabled:opacity-50"
        >
          Security Review
        </button>
        <button
          onClick={() => handleChipClick('Generate pytest unit test suite for selected file.')}
          disabled={isGenerating}
          className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] whitespace-nowrap transition-colors disabled:opacity-50"
        >
          Generate Tests
        </button>
        <button
          onClick={handleScrollToBottom}
          className="ml-auto p-1 rounded-full bg-slate-800/60 hover:bg-slate-700 text-slate-500 hover:text-slate-300 transition-colors flex items-center"
          title="Scroll to latest"
        >
          <ChevronDown className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* ── Input (always visible, sticky at bottom) ── */}
      <form
        onSubmit={handleSend}
        className="p-3 border-t border-slate-800 bg-slate-900/80 flex gap-2 items-end shrink-0"
      >
        <textarea
          placeholder={
            isGenerating
              ? 'AI is thinking… (Shift+Enter for new line)'
              : 'Ask the AI co-pilot… (Enter to send)'
          }
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={textareaRows}
          className="flex-1 min-w-0 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none leading-relaxed transition-colors"
          style={{ minHeight: '34px', maxHeight: '96px' }}
        />
        <button
          type="submit"
          disabled={isGenerating || !inputQuery.trim()}
          className="p-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white disabled:opacity-40 transition-all shadow-glow shrink-0 self-end"
          title="Send (Enter)"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
