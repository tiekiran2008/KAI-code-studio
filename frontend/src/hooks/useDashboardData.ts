import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { reviewsApi } from '../api/reviews';

export const useDashboardData = () => {
  const { data: repositories, isLoading: isLoadingRepos } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => api.getRepositories(),
  });

  const { data: sessions, isLoading: isLoadingSessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.getSessions(),
  });

  const { data: analytics, isLoading: isLoadingAnalytics } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => api.getAnalytics(),
  });

  const { data: memories, isLoading: isLoadingMemories } = useQuery({
    queryKey: ['memories', 'dashboard'],
    queryFn: () => api.getMemories(),
  });

  const { data: reviews, isLoading: isLoadingReviews } = useQuery({
    queryKey: ['reviews', 'recent'],
    queryFn: async () => {
      try {
        return await reviewsApi.listReviews();
      } catch {
        return [];
      }
    },
  });

  const isLoading = isLoadingRepos || isLoadingSessions || isLoadingAnalytics || isLoadingMemories;

  return {
    repositories: repositories || [],
    sessions: sessions || [],
    analytics,
    memories: memories || [],
    reviews: reviews || [],
    isLoadingReviews,
    isLoading,
  };
};
