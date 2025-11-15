// src/config/env.ts
import Constants from 'expo-constants';

export const ENV = {
  API_BASE_URL: 
    process.env.EXPO_PUBLIC_API_URL || 
    Constants.expoConfig?.extra?.apiUrl || 
    'http://192.168.0.122:8000',
  
  WS_BASE_URL: 
    process.env.EXPO_PUBLIC_WS_URL || 
    Constants.expoConfig?.extra?.wsUrl || 
    'ws://192.168.0.122:8000',
  
  IS_DEV: __DEV__,
  
  ENABLE_HITL: process.env.EXPO_PUBLIC_ENABLE_HITL === 'true' || true
};

// Log configuration in development
if (__DEV__) {
  console.log('🔧 Environment Configuration:', ENV);
}
