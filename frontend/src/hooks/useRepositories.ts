import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { useUIStore } from '../store/useUIStore';

export const useRepositories = () => {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  const { data: repositories = [], isLoading, error } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => api.getRepositories(),
  });

  const importMutation = useMutation({
    mutationFn: ({ url, branch }: { url: string; branch: string }) =>
      api.importRepository(url, branch),
    onSuccess: (newRepo) => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      addToast(`Repository ${newRepo.name} imported and indexed!`, 'success');
    },
    onError: () => {
      addToast('Failed to import repository.', 'error');
    },
  });

  const uploadMutation = useMutation({
    mutationFn: ({ name, file }: { name: string; file?: File }) =>
      api.uploadLocalRepository(name, file),
    onSuccess: (newRepo) => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      addToast(`Local repository ${newRepo.name} uploaded!`, 'success');
    },
    onError: () => {
      addToast('Failed to upload local repository.', 'error');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (repoId: string) => api.deleteRepository(repoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      addToast('Repository deleted successfully.', 'success');
    },
    onError: () => {
      addToast('Failed to delete repository.', 'error');
    },
  });

  const reindexMutation = useMutation({
    mutationFn: (repoId: string) => api.reindexRepository(repoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      addToast('Re-indexing pipeline initiated.', 'info');
    },
    onError: () => {
      addToast('Failed to start re-indexing.', 'error');
    },
  });

  return {
    repositories,
    isLoading,
    error,
    importRepo: importMutation.mutateAsync,
    isImporting: importMutation.isPending,
    uploadRepo: uploadMutation.mutateAsync,
    isUploading: uploadMutation.isPending,
    deleteRepo: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    reindexRepo: reindexMutation.mutateAsync,
    isReindexing: reindexMutation.isPending,
  };
};
