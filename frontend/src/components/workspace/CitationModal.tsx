import React from 'react';
import { BookOpen, X } from 'lucide-react';
import { Citation } from '../../types';

interface CitationModalProps {
  citation: Citation | null;
  onClose: () => void;
}

export const CitationModal: React.FC<CitationModalProps> = ({ citation, onClose }) => {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#0f172a] border border-cyan-500/30 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 text-cyan-400">
            <BookOpen className="w-5 h-5" />
            <h3 className="text-sm font-bold text-white font-mono">{citation.file_path}</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Lines: {citation.start_line} - {citation.end_line}</span>
            {citation.score && <span>Relevance: {(citation.score * 100).toFixed(1)}%</span>}
          </div>
          <pre className="p-4 rounded-xl bg-slate-950 text-xs font-mono text-cyan-200 border border-slate-800 overflow-x-auto max-h-80 leading-relaxed">
            {citation.snippet}
          </pre>
        </div>

        <div className="flex justify-end border-t border-slate-800 pt-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 text-xs font-medium text-slate-300 hover:text-white"
          >
            Close Reference
          </button>
        </div>
      </div>
    </div>
  );
};
