export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

interface FetchOptions extends Omit<RequestInit, 'body'> {
  body?: any;
  params?: Record<string, string | number | boolean | undefined>;
}

export function getApiBaseUrl(): string {
  const rawBase = (
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    ''
  ).trim();

  const rawPrefix = (import.meta.env.VITE_API_PREFIX || '/api/v1').trim();
  const prefix = rawPrefix.startsWith('/') ? rawPrefix : `/${rawPrefix}`;

  if (rawBase) {
    const trimmedBase = rawBase.replace(/\/+$/, '');

    if (trimmedBase.endsWith('/api/v1')) {
      return trimmedBase;
    }

    return `${trimmedBase}${prefix}`.replace(/\/+$/, '');
  }

  return prefix.replace(/\/+$/, '');
}

export function buildApiUrl(endpoint: string): string {
  let cleanEndpoint = endpoint.trim();

  if (!cleanEndpoint.startsWith('/')) {
    cleanEndpoint = `/${cleanEndpoint}`;
  }

  if (cleanEndpoint.startsWith('/api/v1/')) {
    cleanEndpoint = cleanEndpoint.substring('/api/v1'.length);
  } else if (cleanEndpoint === '/api/v1') {
    cleanEndpoint = '';
  }

  return `${getApiBaseUrl()}${cleanEndpoint}`;
}

/**
 * Uses the current Supabase session when configured.
 * Legacy token storage is used only without Supabase.
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    const { supabase, isSupabaseConfigured } =
      await import('../lib/supabase');

    if (isSupabaseConfigured) {
      if (!supabase) return null;

      const { data, error } = await supabase.auth.getSession();

      if (error) return null;

      return data.session?.access_token?.trim() || null;
    }
  } catch {
    // Do not fall back to cached tokens if Supabase initialization fails.
    return null;
  }

  // Legacy authentication for setups without Supabase.
  try {
    const flatToken =
      localStorage.getItem('access_token') ||
      localStorage.getItem('auth_token');

    if (flatToken?.trim()) {
      return flatToken.trim();
    }

    const authStorage = localStorage.getItem('auth-storage');

    if (authStorage) {
      const parsed = JSON.parse(authStorage);
      const token = parsed?.state?.accessToken;

      if (typeof token === 'string' && token.trim()) {
        return token.trim();
      }
    }
  } catch { }

  return null;
}

export function getAuthUser(): { id?: string; email?: string } | null {
  try {
    const userJson =
      localStorage.getItem('user') || localStorage.getItem('auth_user');

    if (userJson) {
      const parsed = JSON.parse(userJson);
      if (parsed?.id) return parsed;
    }
  } catch { }

  try {
    const authStorage = localStorage.getItem('auth-storage');

    if (authStorage) {
      const parsed = JSON.parse(authStorage);
      if (parsed?.state?.user?.id) return parsed.state.user;
    }
  } catch { }

  return null;
}

async function client<T>(
  endpoint: string,
  options: FetchOptions = {},
): Promise<T> {
  const { body, params, headers, ...customConfig } = options;

  let url = buildApiUrl(endpoint);

  if (params) {
    const searchParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });

    const queryString = searchParams.toString();

    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  const config: RequestInit = {
    ...customConfig,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (body !== undefined) {
    if (body instanceof FormData) {
      if (
        config.headers &&
        'Content-Type' in (config.headers as Record<string, string>)
      ) {
        delete (config.headers as Record<string, string>)['Content-Type'];
      }

      config.body = body;
    } else {
      config.body = JSON.stringify(body);
    }
  }

  // Attach a Bearer token unless the caller explicitly provided one.
  const headerRecord = config.headers as Record<string, string>;
  const hasExistingAuth =
    headerRecord &&
    (headerRecord['Authorization'] || headerRecord['authorization']);

  if (!hasExistingAuth) {
    const token = await getAuthToken();

    if (token && headerRecord) {
      headerRecord['Authorization'] = `Bearer ${token}`;
    }
  }

  // Do not automatically add X-User-ID.
  // Callers that require it must pass it explicitly through options.headers.

  let response: Response;

  try {
    response = await fetch(url, config);
  } catch (err: any) {
    throw new ApiError(0, 'Network error. Please check your connection.', {
      originalError: err,
    });
  }

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
  }

  let data;
  const contentType = response.headers.get('content-type');

  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    data = await response.text();
  }

  if (response.ok) {
    return data as T;
  }

  let errorMsg = '';

  if (data) {
    if (typeof data === 'string') {
      if (data.trim().startsWith('<') || data.includes('<html>')) {
        errorMsg = response.statusText || `Server error (${response.status})`;
      } else {
        errorMsg = data;
      }
    } else if (typeof data.detail === 'string') {
      errorMsg = data.detail;
    } else if (Array.isArray(data.detail)) {
      errorMsg = data.detail
        .map(
          (d: any) =>
            d.msg || (typeof d === 'string' ? d : JSON.stringify(d)),
        )
        .join(', ');
    } else if (typeof data.message === 'string') {
      errorMsg = data.message;
    } else if (typeof data.error === 'string') {
      errorMsg = data.error;
    }
  }

  if (!errorMsg || !errorMsg.trim()) {
    if (response.status === 429) {
      errorMsg = 'AI provider rate limit reached. Please retry shortly.';
    } else {
      errorMsg =
        response.statusText ||
        (response.status === 500
          ? 'Internal Server Error (500)'
          : `HTTP Error ${response.status}`);
    }
  }

  throw new ApiError(response.status, errorMsg, data);
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 0) {
      return 'Network error. Please check your connection.';
    }

    if (error.status === 400) {
      return error.message || 'Invalid request.';
    }

    if (error.status === 401) {
      return 'Session expired. Please log in again.';
    }

    if (error.status === 403) {
      return 'Permission denied.';
    }

    if (error.status === 404) {
      return 'Resource not found.';
    }

    if (error.status === 409) {
      return error.message || 'Conflict detected.';
    }

    if (error.status === 429) {
      return error.message || 'Rate limit reached. Please retry shortly.';
    }

    if (error.status >= 500) {
      return 'Internal server error. Please try again later.';
    }

    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred.';
}

export const fetchClient = {
  get: <T>(endpoint: string, options?: FetchOptions) =>
    client<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: any, options?: FetchOptions) =>
    client<T>(endpoint, { ...options, body, method: 'POST' }),

  put: <T>(endpoint: string, body?: any, options?: FetchOptions) =>
    client<T>(endpoint, { ...options, body, method: 'PUT' }),

  patch: <T>(endpoint: string, body?: any, options?: FetchOptions) =>
    client<T>(endpoint, { ...options, body, method: 'PATCH' }),

  delete: <T>(endpoint: string, options?: FetchOptions) =>
    client<T>(endpoint, { ...options, method: 'DELETE' }),
};