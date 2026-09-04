import React from 'react';
import { MemoryRecord } from '../../types';
import { Activity, Star } from 'lucide-react';

interface RecentActivityTimelineProps {
  memories: MemoryRecord[];
}

export const RecentActivityTimeline: React.FC<RecentActivityTimelineProps> = ({ memories }) => {
  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-emerald-400" />
        <h2 className="text-base font-semibold text-white">Recent System Activity</h2>
      </div>

      <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-800 before:to-transparent">
        {memories.length === 0 && (
          <div className="text-sm text-slate-400 text-center py-4">No recent activity.</div>
        )}
        {memories.slice(0, 4).map((memory) => (
          <div key={memory.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
            <div className="flex items-center justify-center w-10 h-10 rounded-full border border-slate-800 bg-slate-900 group-hover:bg-emerald-500/20 group-hover:border-emerald-500/30 text-slate-500 group-hover:text-emerald-400 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors">
              <Star className="w-4 h-4" />
            </div>
            
            <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl glass-card hover:border-emerald-500/30 transition-colors">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-sm text-slate-200 capitalize">{memory.memoryType.replace('_', ' ')}</span>
                <span className="text-[11px] text-slate-500">
                  {new Date(memory.createdAt).toLocaleDateString()}
                </span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-2">
                {memory.content}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
