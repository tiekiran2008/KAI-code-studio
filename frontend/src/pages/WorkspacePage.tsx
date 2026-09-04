import React, { useState } from 'react';
import { useRepoStore } from '../store/useRepoStore';
import { useChatStore } from '../store/useChatStore';
import { RepoExplorer } from '../components/workspace/RepoExplorer';
import { CodeEditorPanel } from '../components/workspace/CodeEditorPanel';
import { AIChatPanel } from '../components/workspace/AIChatPanel';
import { CitationModal } from '../components/workspace/CitationModal';
import { Citation } from '../types';

export const WorkspacePage: React.FC = () => {
  const { 
    activeRepo, 
    fileTree, 
    selectedFile, 
    setSelectedFile, 
    openTabs, 
    closeTab, 
    setSelectedBranch 
  } = useRepoStore();

  const { activeSession } = useChatStore();
  const session = activeSession();

  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  return (
    <div className="h-[calc(100vh-6.5rem)] flex gap-3 overflow-hidden animate-in fade-in duration-300">
      {/* LEFT PANEL: File Tree & Repository Explorer */}
      <RepoExplorer
        activeRepo={activeRepo}
        fileTree={fileTree}
        selectedFile={selectedFile}
        onSelectFile={(file) => setSelectedFile(file)}
        onSelectBranch={(branch) => setSelectedBranch(branch)}
      />

      {/* CENTER PANEL: Monaco Editor */}
      <CodeEditorPanel
        openTabs={openTabs}
        selectedFile={selectedFile}
        onSelectTab={(file) => setSelectedFile(file)}
        onCloseTab={(fileId) => closeTab(fileId)}
      />

      {/* RIGHT PANEL: AI Engineering Co-Pilot & Chat */}
      <AIChatPanel
        session={session}
        activeRepoId={activeRepo?.id}
        onSelectCitation={(citation) => setSelectedCitation(citation)}
      />

      {/* Citation Details Modal */}
      <CitationModal
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
};
