import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { reviewsApi, CodeReview, StartReviewParams } from '../api/reviews';
import { useUIStore } from './useUIStore';

interface ReviewState {
  activeReview: CodeReview | null;
  history: CodeReview[];
  isLoading: boolean;
  error: string | null;

  startReview: (params: StartReviewParams) => Promise<string | undefined>;
  fetchReview: (id: string) => Promise<void>;
  fetchHistory: (repositoryId: string) => Promise<void>;
  fetchUserReviews: (params?: { repository_id?: string; status?: string }) => Promise<void>;
  clearActiveReview: () => void;
  deleteReview: (id: string) => Promise<void>;
}

export const useReviewStore = create<ReviewState>()(
  persist(
    (set, _get) => ({
      activeReview: null,
      history: [],
      isLoading: false,
      error: null,

      startReview: async (params) => {
        set({ isLoading: true, error: null });
        try {
          const res = await reviewsApi.startReview(params);
          useUIStore.getState().addToast('Code review started successfully', 'success');
          return res.review_id;
        } catch (err: any) {
          set({ error: err.message || 'Failed to start review' });
          useUIStore.getState().addToast('Failed to start review', 'error');
        } finally {
          set({ isLoading: false });
        }
      },

      fetchReview: async (id) => {
        set({ isLoading: true, error: null });
        try {
          const review = await reviewsApi.getReview(id);
          set({ activeReview: review });
        } catch (err: any) {
          set({ error: err.message || 'Failed to fetch review' });
        } finally {
          set({ isLoading: false });
        }
      },

      fetchHistory: async (repositoryId) => {
        set({ isLoading: true, error: null });
        try {
          const history = await reviewsApi.getReviewHistory(repositoryId);
          set({ history });
        } catch (err: any) {
          set({ error: err.message || 'Failed to fetch history' });
        } finally {
          set({ isLoading: false });
        }
      },

      fetchUserReviews: async (params) => {
        set({ isLoading: true, error: null });
        try {
          const history = await reviewsApi.listReviews(params);
          set({ history });
        } catch (err: any) {
          set({ error: err.message || 'Failed to fetch review history' });
        } finally {
          set({ isLoading: false });
        }
      },

      clearActiveReview: () => set({ activeReview: null }),

      deleteReview: async (id) => {
        try {
          await reviewsApi.deleteReview(id);
          set((state) => ({
            history: state.history.filter((r) => r.id !== id),
            activeReview: state.activeReview?.id === id ? null : state.activeReview,
          }));
          useUIStore.getState().addToast('Review deleted', 'success');
        } catch {
          useUIStore.getState().addToast('Failed to delete review', 'error');
        }
      },
    }),
    {
      name: 'review-store',
      partialize: (state) => ({ history: state.history }),
    }
  )
);
