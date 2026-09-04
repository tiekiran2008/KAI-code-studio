import React, { useState } from 'react';
import { useMemories } from '../hooks/useMemories';
import { LoadingScreen } from '../components/common/LoadingScreen';
import { 
  BrainCircuit, 
  Search, 
  Trash2, 
  Lock, 
  Unlock, 
  Tag 
} from 'lucide-react';

export const MemoryCenterPage: React.FC = () => {
  const { memories, isLoading, deleteMemory, searchMemories } = useMemories();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSearching(true);
    await searchMemories(searchQuery);
    setIsSearching(false);
  };

  const filteredMemories = memories.filter((m) => {
    if (selectedType !== 'all' && m.memoryType !== selectedType) return false;
    return true;
  });

  if (isLoading) {
    return <LoadingScreen isLoading={true} message="Loading memory center..." fullScreen={false} />;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-purple-400" /> Intelligent Memory Center
          </h1>
          <p className="text-xs text-slate-400">
            Stores short-term session state, long-term user preferences, repository architectural summaries, and episodic debugging traces.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs px-3 py-1.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-300 font-mono">
            {memories.length} Records Persisted
          </span>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2 w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search memories using hybrid vector similarity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs shadow-glow transition-all"
          >
            {isSearching ? 'Searching...' : 'Search'}
          </button>
        </form>

        <div className="flex gap-1.5 overflow-x-auto w-full md:w-auto">
          {['all', 'long_term', 'repository', 'episodic', 'short_term'].map((type) => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`px-3 py-1.5 rounded-xl text-xs font-mono transition-all capitalize ${
                selectedType === type
                  ? 'bg-purple-600 text-white shadow-glow'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {type.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Memory Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredMemories.map((mem) => (
          <div
            key={mem.id}
            className="glass-card p-5 rounded-2xl space-y-4 border border-slate-800 hover:border-purple-500/40 flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-300 font-mono border border-purple-500/20 uppercase tracking-wider">
                  {mem.memoryType.replace('_', ' ')}
                </span>
                <div className="flex items-center gap-1.5 text-xs text-slate-400">
                  {mem.isEncrypted ? (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                      <Lock className="w-3 h-3" /> Encrypted
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] text-slate-500 font-mono">
                      <Unlock className="w-3 h-3" /> Plaintext
                    </span>
                  )}
                </div>
              </div>

              <p className="text-xs text-slate-200 leading-relaxed font-sans">
                "{mem.content}"
              </p>

              {mem.techStack && mem.techStack.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {mem.techStack.map((tech) => (
                    <span
                      key={tech}
                      className="px-2 py-0.5 rounded bg-slate-900 text-[10px] font-mono text-cyan-300 border border-slate-800 flex items-center gap-1"
                    >
                      <Tag className="w-2.5 h-2.5 text-cyan-400" /> {tech}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
              <div className="text-[11px] text-slate-400 font-mono">
                Importance: {(mem.importanceScore * 100).toFixed(0)}%
              </div>

              <button
                onClick={() => deleteMemory(mem.id)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="GDPR Right-to-Erasure Physical Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
