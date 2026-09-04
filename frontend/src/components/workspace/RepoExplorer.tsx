import React, { useState } from 'react';
import { 
  GitBranch, 
  Search, 
  FileCode, 
  Folder, 
  FolderOpen, 
  ChevronRight, 
  ChevronDown 
} from 'lucide-react';
import { FileNode, Repository } from '../../types';

interface RepoExplorerProps {
  activeRepo: Repository | null;
  fileTree: FileNode[];
  selectedFile: FileNode | null;
  onSelectFile: (file: FileNode) => void;
  onSelectBranch: (branch: string) => void;
}

export const RepoExplorer: React.FC<RepoExplorerProps> = ({
  activeRepo,
  fileTree,
  selectedFile,
  onSelectFile,
  onSelectBranch,
}) => {
  const [fileSearch, setFileSearch] = useState('');
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    'f-1': true,
    'f-1-1': true,
    'f-1-1-2': true,
    'f-1-1-2-1': true,
    'f-2': true,
  });

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

      const isSelected = selectedFile?.id === node.id;
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
    <div className="w-64 glass-panel rounded-2xl flex flex-col overflow-hidden shrink-0 border border-slate-800">
      <div className="p-3 border-b border-slate-800 space-y-2 bg-slate-900/60">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-indigo-400" /> Explorer
          </span>
          {activeRepo && (
            <select
              value={activeRepo.currentBranch}
              onChange={(e) => onSelectBranch(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-[11px] text-indigo-300 font-mono px-2 py-0.5 rounded focus:outline-none focus:border-indigo-500"
            >
              {activeRepo.branches.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          )}
        </div>

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
        {displayTree.length === 0 ? (
          <div className="text-[11px] text-slate-500 text-center py-4">No matching files</div>
        ) : (
          renderTree(displayTree)
        )}
      </div>
    </div>
  );
};
