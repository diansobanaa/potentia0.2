// src/features/auth/store/authStore.ts
import { create } from 'zustand';
import { authApi } from '@services/api/auth.api';
import { 
  saveToken, 
  saveRefreshToken, 
  saveUser, 
  getToken, 
  getUser, 
  clearAuth 
} from '@services/storage/SecureStorage';
import type { User, LoginRequest, RegisterRequest } from '@types/auth.types';

interface AuthState {
  // State
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  // Initial state
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  // Login action
  login: async (credentials: LoginRequest) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authApi.login(credentials);
      
      // Save to secure storage
      await saveToken(response.access_token);
      await saveRefreshToken(response.refresh_token);
      await saveUser(response.user);
      
      set({
        user: response.user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed';
      set({ 
        error: errorMessage, 
        isLoading: false,
        isAuthenticated: false 
      });
      throw error;
    }
  },

  // Register action
  register: async (userData: RegisterRequest) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authApi.register(userData);
      
      // Save to secure storage
      await saveToken(response.access_token);
      await saveRefreshToken(response.refresh_token);
      await saveUser(response.user);
      
      set({
        user: response.user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Registration failed';
      set({ 
        error: errorMessage, 
        isLoading: false,
        isAuthenticated: false 
      });
      throw error;
    }
  },

  // Logout action
  logout: async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      // Clear storage regardless of API call result
      await clearAuth();
      
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        error: null,
      });
    }
  },

  // Refresh token action
  refreshToken: async () => {
    try {
      const refreshToken = await getToken(); // You might want getRefreshToken here
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      
      const response = await authApi.refreshToken(refreshToken);
      await saveToken(response.access_token);
      
      set({ token: response.access_token });
    } catch (error) {
      console.error('Token refresh failed:', error);
      await get().logout();
      throw error;
    }
  },

  // Load user from storage (on app start)
  loadUser: async () => {
    try {
      const token = await getToken();
      const user = await getUser();
      
      if (token && user) {
        set({
          token,
          user,
          isAuthenticated: true,
        });
      }
    } catch (error) {
      console.error('Failed to load user:', error);
      await clearAuth();
    }
  },

  // Clear error
  clearError: () => set({ error: null }),
}));
