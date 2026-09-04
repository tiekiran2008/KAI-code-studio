import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export const useTools = () => {
  const { data: tools = [], isLoading } = useQuery({
    queryKey: ['tools'],
    queryFn: () => api.getRegisteredTools(),
  });

  return {
    tools,
    isLoading,
  };
};
