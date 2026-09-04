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

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

async function client<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { body, params, headers, ...customConfig } = options;

  let url = `${BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const config: RequestInit = {
    ...customConfig,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const token = localStorage.getItem('auth_token');
  if (token && config.headers) {
    (config.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, config);
  } catch {
    throw new Error('Network error. Please check your connection.');
  }

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
  }

  let data;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (response.ok) {
    return data as T;
  } else {
    throw new ApiError(response.status, data?.message || response.statusText, data);
  }
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
