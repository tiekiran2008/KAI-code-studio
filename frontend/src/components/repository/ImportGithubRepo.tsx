import React, { useState } from 'react';
import { Github, GitBranch, RefreshCw } from 'lucide-react';

interface ImportGithubRepoProps {
  onImport: (url: string, branch: string) => Promise<void>;
  isImporting: boolean;
}

export const ImportGithubRepo: React.FC<ImportGithubRepoProps> = ({ onImport, isImporting }) => {
  const [importUrl, setImportUrl] = useState('');
  const [importBranch, setImportBranch] = useState('main');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importUrl) return;
    await onImport(importUrl, importBranch);
    setImportUrl('');
  };

  return (
    <div className="glass-panel p-8 rounded-2xl max-w-2xl mx-auto space-y-6">
      <div className="space-y-1">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Github className="w-5 h-5 text-indigo-400" /> Import GitHub Repository
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          Enter a GitHub URL to index the codebase. The ingestion engine parses ASTs, calculates vector embeddings, and builds code dependency graphs.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300">GitHub Repository URL</label>
          <input
            type="url"
            required
            placeholder="https://github.com/owner/repository"
            value={importUrl}
            onChange={(e) => setImportUrl(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Default Branch</label>
            <input
              type="text"
              value={importBranch}
              onChange={(e) => setImportBranch(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Access Token (Optional)</label>
            <input
              type="password"
              placeholder="ghp_••••••••••••"
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isImporting}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm shadow-glow flex items-center justify-center gap-2 transition-all disabled:opacity-50"
        >
          {isImporting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" /> Indexing Repository Chunks...
            </>
          ) : (
            <>
              <GitBranch className="w-4 h-4" /> Import & Index Repository
            </>
          )}
        </button>
      </form>
    </div>
  );
};
