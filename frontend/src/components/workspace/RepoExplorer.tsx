import React, { useState, useEffect } from 'react';
import { 
  GitBranch, 
  Search, 
  FileCode, 
  Folder, 
  FolderOpen, 
  ChevronRight, 
  ChevronDown,
  RefreshCw,
  AlertCircle,
  FolderTree
} from 'lucide-react';
import { FileNode, Repository } from '../../types';

interface RepoExplorerProps {
  activeRepo: Repository | null;
  fileTree: FileNode[];
  selectedFile: FileNode | null;
  isLoading?: boolean;
  error?: string | null;
  onSelectFile: (file: FileNode) => void;
  onSelectBranch: (branch: string) => void;
  onRefresh?: () => void;
}

export const RepoExplorer: React.FC<RepoExplorerProps> = ({
  activeRepo,
  fileTree,
  selectedFile,
  isLoading = false,
  error = null,
  onSelectFile,
  onSelectBranch,
  onRefresh,
}) => {
  const [fileSearch, setFileSearch] = useState('');
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});

  // Auto-expand top level directories when fileTree changes
  useEffect(() => {
    if (fileTree && fileTree.length > 0) {
      const topLevelDirs: Record<string, boolean> = {};
      fileTree.forEach((node) => {
        if (node.type === 'directory') {
          topLevelDirs[node.id] = true;
        }
      });
      setExpandedFolders((prev) => ({ ...topLevelDirs, ...prev }));
    }
  }, [fileTree]);

  const toggleFolder = (folderId: string) => {
    setExpandedFolders((prev) => ({ ...prev, [folderId]: !prev[folderId] }));
  };

  const filterTree = (nodes: FileNode[], query: string): FileNode[] => {
    if (!query) return nodes;
    const lowerQuery = query.toLowerCase();

    return nodes.reduce<FileNode[]>((acc, node) => {
      if (node.type === 'file') {
        if (node.name.toLowerCase().includes(lowerQuery) || node.path.toLowerCase().includes(lowerQuery)) {
          acc.push(node);
        }
      } else if (node.type === 'directory' && node.children) {
        const filteredChildren = filterTree(node.children, query);
        if (filteredChildren.length > 0 || node.name.toLowerCase().includes(lowerQuery)) {
          acc.push({ ...node, children: filteredChildren });
        }
      }
      return acc;
    }, []);
  };

  const displayTree = filterTree(fileTree, fileSearch);

  const currentBranch =
    activeRepo?.current_branch ||
    activeRepo?.currentBranch ||
    activeRepo?.default_branch ||
    activeRepo?.defaultBranch ||
    'main';

  const branches = activeRepo?.branches && activeRepo.branches.length > 0
    ? activeRepo.branches
    : [currentBranch];

  const renderTree = (nodes: FileNode[], depth = 0) => {
    return nodes.map((node) => {
      if (node.type === 'directory') {
        const isExpanded = expandedFolders[node.id] || Boolean(fileSearch);
        return (
          <div key={node.id}>
            <button
              onClick={() => toggleFolder(node.id)}
              style={{ paddingLeft: `${depth * 12 + 8}px` }}
              className="w-full flex items-center gap-1.5 py-1 text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 rounded-md transition-colors text-left"
            >
              {isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              )}
              {isExpanded ? (
                <FolderOpen className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              ) : (
                <Folder className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              )}
              <span className="truncate">{node.name}</span>
            </button>
            {isExpanded && node.children && renderTree(node.children, depth + 1)}
          </div>
        );
      }

      const isSelected = selectedFile?.id === node.id || selectedFile?.path === node.path;
      return (
        <button
          key={node.id}
          onClick={() => onSelectFile(node)}
          style={{ paddingLeft: `${depth * 12 + 20}px` }}
          className={`w-full flex items-center gap-2 py-1 text-xs rounded-md transition-colors text-left ${
            isSelected
              ? 'bg-indigo-600/30 text-indigo-200 font-medium border-l-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span className="truncate">{node.name}</span>
        </button>
      );
    });
  };

  return (
    <div className="w-[280px] min-w-[280px] max-w-[280px] glass-panel rounded-2xl flex flex-col overflow-hidden shrink-0 border border-slate-800">
      <div className="p-3 border-b border-slate-800 space-y-2 bg-slate-900/60">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-indigo-400" /> Explorer
          </span>
          <div className="flex items-center gap-1.5">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isLoading}
                className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors disabled:opacity-50"
                title="Refresh File Tree"
              >
                <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            )}
            {activeRepo && (
              <select
                value={currentBranch}
                onChange={(e) => onSelectBranch(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-[11px] text-indigo-300 font-mono px-2 py-0.5 rounded focus:outline-none focus:border-indigo-500 max-w-[110px] truncate"
              >
                {branches.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {activeRepo && (
          <div className="text-[11px] font-medium text-slate-300 truncate flex items-center gap-1 bg-slate-950/60 px-2 py-1 rounded-lg border border-slate-800/50">
            <FolderTree className="w-3 h-3 text-indigo-400 shrink-0" />
            <span className="truncate">{activeRepo.name}</span>
          </div>
        )}

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search files..."
            value={fileSearch}
            onChange={(e) => setFileSearch(e.target.value)}
            className="w-full bg-slate-950 text-slate-200 text-xs pl-8 pr-3 py-1.5 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="text-center py-8 space-y-2 text-slate-400">
            <RefreshCw className="w-4 h-4 animate-spin text-indigo-400 mx-auto" />
            <p className="text-xs">Loading files...</p>
          </div>
        ) : error ? (
          <div className="text-center py-6 px-2 space-y-2 text-rose-400">
            <AlertCircle className="w-4 h-4 mx-auto text-rose-400" />
            <p className="text-[11px]">{error}</p>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="text-[10px] px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition-colors"
              >
                Retry
              </button>
            )}
          </div>
        ) : displayTree.length === 0 ? (
          <div className="text-[11px] text-slate-500 text-center py-8">
            {fileSearch ? 'No matching files' : 'No files in repository'}
          </div>
        ) : (
          renderTree(displayTree)
        )}
      </div>
    </div>
  );
};
