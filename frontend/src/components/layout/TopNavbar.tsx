import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useUIStore } from '../../store/useUIStore';
import { useSettingsStore } from '../../store/useSettingsStore';
import { useTheme } from '../providers/ThemeProvider';
import { Search, Activity, Sun, Moon, UserCircle } from 'lucide-react';
import { navItems } from './Sidebar';
import { WorkspaceSwitcher } from '../workspace/WorkspaceSwitcher';

export const TopNavbar: React.FC = () => {
  const { setCommandPaletteOpen } = useUIStore();
  const { llm } = useSettingsStore();
  const { theme, setTheme } = useTheme();
  const location = useLocation();

  const currentNav = navItems.find((n) => n.path === location.pathname) || navItems[0];

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <header className="h-16 px-6 bg-[#0f172a]/60 backdrop-blur-md border-b border-slate-800/80 sticky top-0 z-30 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-white tracking-tight flex items-center gap-2">
          {currentNav.name}
        </h1>
        <div className="hidden md:block h-5 w-px bg-slate-700/60 mx-1" />
        <div className="hidden md:block">
          <WorkspaceSwitcher />
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Command Palette Trigger */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 text-xs transition-colors"
        >
          <Search className="w-3.5 h-3.5 text-indigo-400" />
          <span>Search platform...</span>
          <kbd className="bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded text-[10px] font-mono border border-slate-700">
            Cmd+K
          </kbd>
        </button>

        {/* Model Selector Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
          <Activity className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
          <span>{llm?.modelName || 'GPT-4o'}</span>
        </div>

        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
        </button>

        {/* Profile Link */}
        <Link
          to="/profile"
          className={`p-2 rounded-xl border transition-colors ${
            location.pathname === '/profile'
              ? 'bg-indigo-900/30 border-indigo-500/50 text-indigo-400'
              : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700'
          }`}
        >
          <UserCircle className="w-5 h-5" />
        </Link>
      </div>
    </header>
  );
};
