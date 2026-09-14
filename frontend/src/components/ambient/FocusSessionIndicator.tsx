import React from 'react';
import { useThemeStore } from '../../store/useThemeStore';
import { Sparkles, X } from 'lucide-react';

export const FocusSessionIndicator: React.FC = () => {
  const { resolvedTheme, focusSession, setFocusSession } = useThemeStore();

  if (resolvedTheme !== 'ambient' || !focusSession) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-950/70 border border-indigo-500/40 text-indigo-300 text-xs shadow-glow backdrop-blur-md animate-in fade-in duration-200">
      <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
      <span className="font-medium tracking-wide">Focus Session • Active</span>
      <button
        onClick={() => setFocusSession(false)}
        className="ml-1 p-0.5 rounded-full hover:bg-indigo-800/50 text-indigo-400 hover:text-white transition-colors"
        title="Exit Focus Session"
        aria-label="Exit Focus Session"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
};
