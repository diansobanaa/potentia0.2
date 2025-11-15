// src/types/auth.types.ts
export interface User {
  id: string;
  email: string;
  full_name: string;
  subscription_tier: 'free' | 'pro' | 'enterprise';
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
}
