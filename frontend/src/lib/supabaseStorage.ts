import { supabase, isSupabaseConfigured } from './supabase';

/**
 * Safely removes an image from Supabase Storage if the URL corresponds
 * to an object stored in a Supabase Storage bucket.
 * 
 * Silently catches and logs errors so that storage failures never prevent
 * the profile photo removal from completing successfully in the database.
 */
export async function deleteSupabaseStorageAvatar(avatarUrl: string | null | undefined): Promise<boolean> {
  if (!avatarUrl || typeof avatarUrl !== 'string') {
    return false;
  }

  // Check if URL matches a Supabase storage endpoint pattern
  // E.g.: https://<project-ref>.supabase.co/storage/v1/object/public/<bucket>/<path>
  // Or: https://<project-ref>.supabase.co/storage/v1/object/sign/<bucket>/<path>
  const storagePatterns = [
    '/storage/v1/object/public/',
    '/storage/v1/object/sign/',
    '/storage/v1/object/authenticated/'
  ];

  let matchedPattern: string | null = null;
  for (const pattern of storagePatterns) {
    if (avatarUrl.includes(pattern)) {
      matchedPattern = pattern;
      break;
    }
  }

  if (!matchedPattern) {
    return false; // Not a Supabase storage URL (e.g. base64 data URI or external URL)
  }

  if (!isSupabaseConfigured || !supabase) {
    return false;
  }

  try {
    const parts = avatarUrl.split(matchedPattern);
    if (parts.length > 1) {
      const pathWithQuery = parts[1];
      const cleanPath = pathWithQuery.split('?')[0]; // remove query params if signed
      const segments = cleanPath.split('/');
      const bucket = segments[0];
      const filePath = segments.slice(1).join('/');

      if (bucket && filePath) {
        const { error } = await supabase.storage.from(bucket).remove([filePath]);
        if (error) {
          console.warn('Warning: Could not remove avatar from Supabase Storage:', error.message);
          return false;
        }
        return true;
      }
    }
  } catch (err) {
    console.warn('Warning: Exception while deleting Supabase Storage avatar:', err);
  }

  return false;
}
