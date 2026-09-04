import React from 'react';
import Editor from '@monaco-editor/react';
import { FileCode, X } from 'lucide-react';
import { FileNode } from '../../types';

interface CodeEditorPanelProps {
  openTabs: FileNode[];
  selectedFile: FileNode | null;
  onSelectTab: (file: FileNode) => void;
  onCloseTab: (fileId: string) => void;
}

export const CodeEditorPanel: React.FC<CodeEditorPanelProps> = ({
  openTabs,
  selectedFile,
  onSelectTab,
  onCloseTab,
}) => {
  return (
    <div className="flex-1 glass-panel rounded-2xl flex flex-col overflow-hidden border border-slate-800">
      {/* Editor Tabs Header */}
      <div className="h-10 bg-slate-950/80 border-b border-slate-800 flex items-center px-2 gap-1 overflow-x-auto">
        {openTabs.map((tab) => {
          const isActive = selectedFile?.id === tab.id;
          return (
            <div
              key={tab.id}
              onClick={() => onSelectTab(tab)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-t-lg text-xs font-mono cursor-pointer border-t border-x transition-colors ${
                isActive
                  ? 'bg-[#1e1e1e] text-indigo-300 border-indigo-500/50 font-semibold'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span className="truncate max-w-[120px]">{tab.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCloseTab(tab.id);
                }}
                className="p-0.5 text-slate-500 hover:text-white rounded"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>

      {/* Monaco Editor Container */}
      <div className="flex-1 bg-[#1e1e1e] relative">
        {selectedFile ? (
          <Editor
            height="100%"
            language={selectedFile.language || 'python'}
            theme="vs-dark"
            value={selectedFile.content || `// Viewing ${selectedFile.name}\n// Use the AI chat on the right to analyze this code.`}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              fontSize: 13,
              fontFamily: "'JetBrains Mono', monospace",
              scrollBeyondLastLine: false,
              smoothScrolling: true,
              automaticLayout: true,
            }}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs space-y-2">
            <FileCode className="w-8 h-8 text-slate-600" />
            <span>Select a file from the left explorer to view code</span>
          </div>
        )}
      </div>
    </div>
  );
};
