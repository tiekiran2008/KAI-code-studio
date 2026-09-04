import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export const useAnalytics = () => {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => api.getAnalytics(),
  });

  return {
    analytics,
    isLoading,
  };
};
