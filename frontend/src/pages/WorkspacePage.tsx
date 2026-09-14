import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useRepoStore } from '../store/useRepoStore';
import { useRepositoryStore } from '../store/repositoryStore';
import { useChatStore } from '../store/useChatStore';
import { RepoExplorer } from '../components/workspace/RepoExplorer';
import { CodeEditorPanel } from '../components/workspace/CodeEditorPanel';
import { AIChatPanel } from '../components/workspace/AIChatPanel';
import { CitationModal } from '../components/workspace/CitationModal';
import { FocusAura } from '../components/ambient/FocusAura';
import { Citation } from '../types';
import { ArrowRight, FolderGit2 } from 'lucide-react';

export const WorkspacePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const { 
    activeRepo, 
    fileTree, 
    selectedFile, 
    selectFile, 
    openTabs, 
    closeTab, 
    setSelectedBranch,
    isLoadingTree,
    treeError,
    isLoadingContent,
    contentError,
    loadFileTree,
    setActiveRepo
  } = useRepoStore();

  const { fetchRepository, selectedRepo } = useRepositoryStore();

  const { activeSession, isGenerating } = useChatStore();
  const session = activeSession();

  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);

  // Read URL query parameter ?repoId=... or sync with repositoryStore
  useEffect(() => {
    const urlRepoId = searchParams.get('repoId');

    const initRepo = async () => {
      if (urlRepoId) {
        if (activeRepo?.id !== urlRepoId) {
          setIsInitializing(true);
          try {
            const repo = await fetchRepository(urlRepoId);
            await setActiveRepo(repo);
          } catch {
            // Error handled in store
          } finally {
            setIsInitializing(false);
          }
        }
      } else if (!activeRepo && selectedRepo) {
        setActiveRepo(selectedRepo);
      } else if (activeRepo && (!fileTree || fileTree.length === 0) && !isLoadingTree) {
        loadFileTree(activeRepo.id);
      }
    };

    initRepo();
  }, [searchParams, activeRepo?.id]);

  // If no active repo selected, show empty state
  if (!activeRepo && !isInitializing) {
    return (
      <div className="h-[calc(100vh-6.5rem)] flex items-center justify-center animate-in fade-in duration-300">
        <div className="glass-panel p-8 rounded-3xl border border-slate-800 text-center max-w-md space-y-4 shadow-2xl shadow-indigo-950/20">
          <div className="w-16 h-16 rounded-2xl bg-indigo-950/60 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <FolderGit2 className="w-8 h-8" />
          </div>

          <div className="space-y-1">
            <h2 className="text-base font-bold text-white">No repository selected</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Select an indexed repository from Repository Manager to browse real files, edit source code, and run AI engineering co-pilot tasks.
            </p>
          </div>

          <div className="pt-2 flex flex-col gap-2">
            <button
              onClick={() => navigate('/repositories')}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 shadow-glow transition-all"
            >
              Open Repository Manager <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="h-[calc(100vh-6.5rem)] w-full overflow-hidden animate-in fade-in duration-300"
      style={{ display: 'grid', gridTemplateColumns: '280px minmax(0, 1fr) clamp(380px, 26vw, 420px)', gap: '0.75rem' }}
    >
      {/* LEFT PANEL: File Tree & Repository Explorer */}
      <FocusAura area="explorer" className="h-full min-w-0 flex flex-col rounded-2xl overflow-hidden">
        <RepoExplorer
          activeRepo={activeRepo}
          fileTree={fileTree}
          selectedFile={selectedFile}
          isLoading={isLoadingTree || isInitializing}
          error={treeError}
          onSelectFile={(file) => selectFile(file)}
          onSelectBranch={(branch) => setSelectedBranch(branch)}
          onRefresh={() => activeRepo && loadFileTree(activeRepo.id)}
        />
      </FocusAura>

      {/* CENTER PANEL: Monaco Editor */}
      <FocusAura area="editor" className="h-full min-w-0 flex flex-col rounded-2xl overflow-hidden">
        <CodeEditorPanel
          openTabs={openTabs}
          selectedFile={selectedFile}
          isLoadingContent={isLoadingContent}
          contentError={contentError}
          onSelectTab={(file) => selectFile(file)}
          onCloseTab={(fileId) => closeTab(fileId)}
        />
      </FocusAura>

      {/* RIGHT PANEL: AI Engineering Co-Pilot & Chat */}
      <FocusAura area="chat" isGenerating={isGenerating} className="h-full min-w-0 flex flex-col rounded-2xl overflow-hidden">
        <AIChatPanel
          session={session}
          activeRepoId={activeRepo?.id}
          activeFilePath={selectedFile?.path}
          onSelectCitation={(citation) => setSelectedCitation(citation)}
        />
      </FocusAura>

      {/* Citation Details Modal */}
      <CitationModal
        citation={selectedCitation}
        onClose={() => setSelectedCitation(null)}
      />
    </div>
  );
};
