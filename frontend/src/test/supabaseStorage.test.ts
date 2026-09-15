import { describe, it, expect, vi, beforeEach } from 'vitest';
import { deleteSupabaseStorageAvatar } from '../lib/supabaseStorage';
import * as supabaseModule from '../lib/supabase';

describe('deleteSupabaseStorageAvatar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns false for null, undefined, or empty string', async () => {
    expect(await deleteSupabaseStorageAvatar(null)).toBe(false);
    expect(await deleteSupabaseStorageAvatar(undefined)).toBe(false);
    expect(await deleteSupabaseStorageAvatar('')).toBe(false);
  });

  it('returns false for base64 data URLs without calling supabase', async () => {
    const base64Avatar = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    const res = await deleteSupabaseStorageAvatar(base64Avatar);
    expect(res).toBe(false);
  });

  it('returns false for external third-party URLs like GitHub or Google avatars', async () => {
    const ghAvatar = 'https://avatars.githubusercontent.com/u/123456?v=4';
    const res = await deleteSupabaseStorageAvatar(ghAvatar);
    expect(res).toBe(false);
  });

  it('extracts bucket and file path and deletes from Supabase storage when URL matches pattern', async () => {
    const mockRemove = vi.fn().mockResolvedValue({ data: [{ name: 'avatar.png' }], error: null });
    const mockFrom = vi.fn().mockReturnValue({ remove: mockRemove });

    vi.spyOn(supabaseModule, 'supabase', 'get').mockReturnValue({
      storage: { from: mockFrom }
    } as any);
    vi.spyOn(supabaseModule, 'isSupabaseConfigured', 'get').mockReturnValue(true);

    const supabaseAvatarUrl = 'https://myproject.supabase.co/storage/v1/object/public/avatars/user-123/avatar.png';
    const res = await deleteSupabaseStorageAvatar(supabaseAvatarUrl);

    expect(mockFrom).toHaveBeenCalledWith('avatars');
    expect(mockRemove).toHaveBeenCalledWith(['user-123/avatar.png']);
    expect(res).toBe(true);
  });

  it('handles Supabase removal errors gracefully without throwing', async () => {
    const mockRemove = vi.fn().mockResolvedValue({ data: null, error: { message: 'Object not found' } });
    const mockFrom = vi.fn().mockReturnValue({ remove: mockRemove });

    vi.spyOn(supabaseModule, 'supabase', 'get').mockReturnValue({
      storage: { from: mockFrom }
    } as any);
    vi.spyOn(supabaseModule, 'isSupabaseConfigured', 'get').mockReturnValue(true);

    const supabaseAvatarUrl = 'https://myproject.supabase.co/storage/v1/object/public/avatars/user-123/avatar.png';
    const res = await deleteSupabaseStorageAvatar(supabaseAvatarUrl);

    expect(res).toBe(false);
  });
});
