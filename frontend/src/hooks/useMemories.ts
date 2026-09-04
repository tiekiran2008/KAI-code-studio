import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { useUIStore } from '../store/useUIStore';

export const useMemories = () => {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();

  const { data: memories = [], isLoading, refetch } = useQuery({
    queryKey: ['memories'],
    queryFn: () => api.getMemories(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      addToast('Memory record physically deleted (GDPR Article 17 Erasure).', 'success');
    },
    onError: () => {
      addToast('Failed to delete memory record.', 'error');
    },
  });

  const searchMemories = async (query: string) => {
    try {
      const results = await api.searchMemories(query);
      queryClient.setQueryData(['memories'], results);
    } catch {
      addToast('Memory search failed.', 'error');
    }
  };

  return {
    memories,
    isLoading,
    deleteMemory: deleteMutation.mutateAsync,
    searchMemories,
    refetch,
  };
};
