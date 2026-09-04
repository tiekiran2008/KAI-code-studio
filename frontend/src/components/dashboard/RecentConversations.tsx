import React from 'react';
import { BrainCircuit, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ConversationSession } from '../../types';

interface RecentConversationsProps {
  sessions: ConversationSession[];
}

export const RecentConversations: React.FC<RecentConversationsProps> = ({ sessions }) => {
  const navigate = useNavigate();

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-purple-400" /> Recent AI Sessions
        </h2>
        <button
          onClick={() => navigate('/workspace')}
          className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
        >
          Open workspace <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      <div className="space-y-3">
        {sessions.length === 0 && (
          <div className="text-sm text-slate-400 text-center py-4">No recent sessions found.</div>
        )}
        {sessions.slice(0, 5).map((session) => (
          <div
            key={session.id}
            onClick={() => navigate('/workspace')}
            className="glass-card p-4 rounded-xl space-y-2 cursor-pointer hover:border-purple-500/40 group transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-sm text-slate-200 group-hover:text-purple-300 transition-colors">
                {session.title}
              </span>
              <span className="text-[11px] text-slate-500">
                {new Date(session.updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
              {session.messages[session.messages.length - 1]?.content || 'Empty conversation'}
            </p>

            <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-500 font-mono">
              <span>{session.messages.length} messages</span>
              <span>•</span>
              <span>Supervisor active</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
