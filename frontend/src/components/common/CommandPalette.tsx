import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '../../store/useUIStore';
import { 
  Search, 
  LayoutDashboard, 
  GitBranch, 
  Code2, 
  Cpu, 
  BrainCircuit, 
  Wrench, 
  BarChart3, 
  Settings,
  X
} from 'lucide-react';

export const CommandPalette: React.FC = () => {
  const { commandPaletteOpen, setCommandPaletteOpen } = useUIStore();
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
      if (e.key === 'Escape' && commandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  if (!commandPaletteOpen) return null;

  const items = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard, category: 'Navigation' },
    { name: 'Repository Manager', path: '/repositories', icon: GitBranch, category: 'Navigation' },
    { name: 'AI Workspace', path: '/workspace', icon: Code2, category: 'Navigation' },
    { name: 'Agent Monitor', path: '/agents', icon: Cpu, category: 'Navigation' },
    { name: 'Memory Center', path: '/memory', icon: BrainCircuit, category: 'Navigation' },
    { name: 'Tool Activity', path: '/tools', icon: Wrench, category: 'Navigation' },
    { name: 'Analytics Dashboard', path: '/analytics', icon: BarChart3, category: 'Navigation' },
    { name: 'Settings', path: '/settings', icon: Settings, category: 'Navigation' },
  ];

  const filteredItems = items.filter((item) =>
    item.name.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (path: string) => {
    navigate(path);
    setCommandPaletteOpen(false);
    setQuery('');
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-24 px-4">
      <div className="bg-[#0f172a] border border-indigo-500/30 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center px-4 py-3 border-b border-slate-800 gap-3">
          <Search className="w-5 h-5 text-indigo-400 shrink-0" />
          <input
            type="text"
            placeholder="Type a command or search platform pages... (Esc to close)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />
          <button
            onClick={() => setCommandPaletteOpen(false)}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="px-4 py-6 text-center text-slate-500 text-sm">
              No matching pages or actions found.
            </div>
          ) : (
            filteredItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.path}
                  onClick={() => handleSelect(item.path)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-indigo-600/20 text-slate-300 hover:text-indigo-200 transition-colors text-sm text-left group"
                >
                  <Icon className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
                  <span className="font-medium flex-1">{item.name}</span>
                  <span className="text-xs text-slate-500 font-mono bg-slate-800/80 px-2 py-0.5 rounded">
                    {item.path}
                  </span>
                </button>
              );
            })
          )}
        </div>

        <div className="px-4 py-2 bg-slate-950/60 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-500">
          <span>Navigation Quick Switch</span>
          <div className="flex gap-2">
            <kbd className="bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700 font-mono">↑↓</kbd> navigate
            <kbd className="bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700 font-mono">↵</kbd> select
          </div>
        </div>
      </div>
    </div>
  );
};
