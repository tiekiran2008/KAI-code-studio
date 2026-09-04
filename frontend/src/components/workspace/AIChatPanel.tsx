import React, { useState } from 'react';
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
  MessageSquare 
} from 'lucide-react';
import { ConversationSession, Citation } from '../../types';
import { useChatStore } from '../../store/useChatStore';

interface AIChatPanelProps {
  session: ConversationSession | undefined;
  activeRepoId?: string;
  onSelectCitation: (citation: Citation) => void;
}

export const AIChatPanel: React.FC<AIChatPanelProps> = ({
  session,
  activeRepoId,
  onSelectCitation,
}) => {
  const { 
    sessions, 
    activeSessionId, 
    setActiveSessionId, 
    sendMessage, 
    createSession, 
    clearSessionMessages, 
    isGenerating 
  } = useChatStore();

  const [inputQuery, setInputQuery] = useState('');
  const [expandedTraceMsgId, setExpandedTraceMsgId] = useState<string | null>(null);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isGenerating) return;
    const text = inputQuery;
    setInputQuery('');
    await sendMessage(text, activeRepoId);
  };

  const handleChipClick = (promptText: string) => {
    setInputQuery(promptText);
  };

  return (
    <div className="w-[380px] glass-panel rounded-2xl flex flex-col overflow-hidden shrink-0 border border-slate-800">
      {/* Chat Header & Session History Selector */}
      <div className="p-3 border-b border-slate-800 bg-slate-900/60 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span className="font-semibold text-xs text-white">AI Engineering Co-Pilot</span>
          </div>
          <button
            onClick={createSession}
            className="p-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs font-medium border border-indigo-500/30 flex items-center gap-1"
            title="Create new session"
          >
            <Plus className="w-3 h-3" /> New
          </button>
        </div>

        {/* Sessions Dropdown */}
        <div className="flex items-center gap-2">
          <MessageSquare className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <select
            value={activeSessionId}
            onChange={(e) => setActiveSessionId(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 text-[11px] text-slate-200 py-1 px-2 rounded-lg focus:outline-none focus:border-indigo-500 truncate"
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
          {session && (
            <button
              onClick={() => clearSessionMessages(session.id)}
              className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
              title="Clear conversation"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Chat Message List */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {session?.messages.length === 0 && (
          <div className="text-center py-8 space-y-2">
            <Bot className="w-8 h-8 text-indigo-400 mx-auto animate-bounce" />
            <p className="text-xs font-medium text-slate-300">How can I assist your engineering work?</p>
            <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
              Ask about codebase architecture, security vulnerabilities, or unit test generation.
            </p>
          </div>
        )}

        {session?.messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col gap-2 ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-mono">
              {msg.role === 'user' ? (
                <>
                  <span>Architect</span> <User className="w-3 h-3 text-indigo-400" />
                </>
              ) : (
                <>
                  <Bot className="w-3 h-3 text-cyan-400" /> <span>Multi-Agent System</span>
                </>
              )}
            </div>

            <div
              className={`p-3.5 rounded-2xl text-xs leading-relaxed max-w-[90%] shadow-lg ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-none'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none space-y-3'
              }`}
            >
              <div className="whitespace-pre-wrap font-sans">{msg.content}</div>

              {/* Multi-Agent Reasoning Trace Accordion */}
              {msg.agentTraces && msg.agentTraces.length > 0 && (
                <div className="pt-2 border-t border-slate-800/80">
                  <button
                    onClick={() =>
                      setExpandedTraceMsgId(expandedTraceMsgId === msg.id ? null : msg.id)
                    }
                    className="flex items-center justify-between w-full text-[11px] text-indigo-400 font-mono hover:underline"
                  >
                    <span className="flex items-center gap-1">
                      <Cpu className="w-3 h-3" /> Multi-Agent Trace ({msg.agentTraces.length} steps)
                    </span>
                    <ChevronRight
                      className={`w-3 h-3 transition-transform ${
                        expandedTraceMsgId === msg.id ? 'rotate-90' : ''
                      }`}
                    />
                  </button>

                  {expandedTraceMsgId === msg.id && (
                    <div className="mt-2 space-y-1.5 pl-2 border-l border-indigo-500/30 text-[10px] font-mono">
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

              {/* Tool Calls Badges */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {msg.toolCalls.map((tc, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-slate-700"
                    >
                      <Wrench className="w-2.5 h-2.5 text-amber-400" />
                      {tc.tool_name} ({tc.latency_ms}ms)
                    </span>
                  ))}
                </div>
              )}

              {/* RAG Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="pt-2 border-t border-slate-800/60 space-y-1">
                  <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                    <BookOpen className="w-3 h-3 text-cyan-400" /> Source Context References:
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

        {isGenerating && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-900/60 text-xs text-indigo-300 font-mono animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
            <span>Multi-Agent Reasoning & Streaming response...</span>
          </div>
        )}
      </div>

      {/* Suggested Action Chips */}
      <div className="p-2 border-t border-slate-800/80 bg-slate-950/40 flex gap-1.5 overflow-x-auto">
        <button
          onClick={() => handleChipClick('Explain function architecture in open file.')}
          className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] whitespace-nowrap transition-colors"
        >
          Explain Architecture
        </button>
        <button
          onClick={() => handleChipClick('Check open file for security OWASP vulnerabilities.')}
          className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] whitespace-nowrap transition-colors"
        >
          Security Review
        </button>
        <button
          onClick={() => handleChipClick('Generate pytest unit test suite for selected file.')}
          className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] whitespace-nowrap transition-colors"
        >
          Generate Unit Tests
        </button>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-3 border-t border-slate-800 bg-slate-900/80 flex gap-2">
        <input
          type="text"
          placeholder="Ask AI Engineer co-pilot..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isGenerating}
          className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={isGenerating || !inputQuery.trim()}
          className="p-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white disabled:opacity-50 transition-all shadow-glow"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
