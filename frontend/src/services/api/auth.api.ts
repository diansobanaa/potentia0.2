// src/services/api/auth.api.ts
import apiClient from './client';
import type { 
  LoginRequest, 
  RegisterRequest, 
  AuthResponse 
} from '@types/auth.types';

export const authApi = {
  /**
   * Login user with email and password
   */
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    const formData = new FormData();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const response = await apiClient.post('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Register new user
   */
  register: async (userData: RegisterRequest): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/v1/auth/register', userData);
    return response.data;
  },

  /**
   * Refresh access token
   */
  refreshToken: async (refreshToken: string): Promise<{ access_token: string }> => {
    const response = await apiClient.post('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  /**
   * Get current user profile
   */
  me: async () => {
    const response = await apiClient.get('/api/v1/auth/me');
    return response.data;
  },

  /**
   * Logout (clear server-side session if needed)
   */
  logout: async (): Promise<void> => {
    // Backend might have logout endpoint
    await apiClient.post('/api/v1/auth/logout');
  },
};
