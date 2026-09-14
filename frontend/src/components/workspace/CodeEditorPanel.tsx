import React from 'react';
import Editor from '@monaco-editor/react';
import { FileCode, X, Loader2 } from 'lucide-react';
import { FileNode } from '../../types';

interface CodeEditorPanelProps {
  openTabs: FileNode[];
  selectedFile: FileNode | null;
  isLoadingContent?: boolean;
  contentError?: string | null;
  onSelectTab: (file: FileNode) => void;
  onCloseTab: (fileId: string) => void;
}

const MONACO_LANG_MAP: Record<string, string> = {
  python: 'python',
  typescript: 'typescript',
  tsx: 'typescript',
  javascript: 'javascript',
  jsx: 'javascript',
  markdown: 'markdown',
  json: 'json',
  yaml: 'yaml',
  html: 'html',
  css: 'css',
  scss: 'scss',
  shell: 'shell',
  powershell: 'powershell',
  sql: 'sql',
  rust: 'rust',
  go: 'go',
  c: 'c',
  cpp: 'cpp',
  csharp: 'csharp',
  java: 'java',
  dockerfile: 'dockerfile',
  text: 'plaintext',
};

export const CodeEditorPanel: React.FC<CodeEditorPanelProps> = ({
  openTabs,
  selectedFile,
  isLoadingContent = false,
  contentError = null,
  onSelectTab,
  onCloseTab,
}) => {
  const getLanguage = (lang?: string, path?: string): string => {
    if (lang && MONACO_LANG_MAP[lang.toLowerCase()]) {
      return MONACO_LANG_MAP[lang.toLowerCase()];
    }
    if (path) {
      if (path.endsWith('.py')) return 'python';
      if (path.endsWith('.ts') || path.endsWith('.tsx')) return 'typescript';
      if (path.endsWith('.js') || path.endsWith('.jsx')) return 'javascript';
      if (path.endsWith('.json')) return 'json';
      if (path.endsWith('.md') || path.toLowerCase() === 'readme') return 'markdown';
      if (path.endsWith('.yml') || path.endsWith('.yaml')) return 'yaml';
      if (path.endsWith('.css')) return 'css';
      if (path.endsWith('.html')) return 'html';
    }
    return 'plaintext';
  };

  return (
    <div className="flex-1 min-w-0 glass-panel rounded-2xl flex flex-col overflow-hidden border border-slate-800">
      {/* Editor Tabs Header */}
      <div className="h-10 bg-slate-950/80 border-b border-slate-800 flex items-center px-2 gap-1 overflow-x-auto min-w-0 shrink-0">
        {openTabs.length === 0 ? (
          <span className="text-xs text-slate-500 italic px-2">No files open</span>
        ) : (
          openTabs.map((tab) => {
            const isActive = selectedFile?.id === tab.id || selectedFile?.path === tab.path;
            return (
              <div
                key={tab.id}
                onClick={() => onSelectTab(tab)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-t-lg text-xs font-mono cursor-pointer border-t border-x transition-colors shrink-0 ${
                  isActive
                    ? 'bg-[#1e1e1e] text-indigo-300 border-indigo-500/50 font-semibold'
                    : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span className="truncate max-w-[140px]">{tab.name}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseTab(tab.id);
                  }}
                  className="p-0.5 text-slate-500 hover:text-white rounded hover:bg-slate-800"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Monaco Editor Container */}
      <div className="flex-1 min-w-0 min-h-0 bg-[#1e1e1e] relative flex flex-col overflow-hidden">
        {contentError && (
          <div className="bg-rose-950/60 border-b border-rose-800/40 text-rose-300 text-xs px-3 py-1.5 flex items-center justify-between shrink-0">
            <span>{contentError}</span>
          </div>
        )}
        {isLoadingContent ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 text-xs space-y-2">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
            <span>Loading file content...</span>
          </div>
        ) : selectedFile ? (
          <Editor
            height="100%"
            width="100%"
            language={getLanguage(selectedFile.language, selectedFile.path)}
            theme="vs-dark"
            value={
              selectedFile.content !== undefined
                ? selectedFile.content
                : `// Loading ${selectedFile.name}...`
            }
            options={{
              readOnly: true,
              minimap: { enabled: true },
              fontSize: 13,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              scrollBeyondLastLine: false,
              smoothScrolling: true,
              automaticLayout: true,
            }}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs space-y-2">
            <FileCode className="w-8 h-8 text-slate-600" />
            <span>Select a file from the Explorer to view code</span>
          </div>
        )}
      </div>
    </div>
  );
};
