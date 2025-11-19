// Lokasi: src/shared/api/supabase.ts

import "react-native-url-polyfill/auto";
import * as SecureStore from "expo-secure-store";
import { createClient } from "@supabase/supabase-js";
import { Platform } from "react-native";
import { env } from "@/src/shared/config/env";
import * as Linking from "expo-linking";

// Cross-platform storage: localStorage (web) and SecureStore (native)
const CrossPlatformStorage = {
  getItem: (key: string) => {
    if (Platform.OS === "web") {
      try {
        return typeof window !== "undefined"
          ? window.localStorage.getItem(key)
          : null;
      } catch {
        return null;
      }
    }
    return SecureStore.getItemAsync(key);
  },
  setItem: (key: string, value: string) => {
    if (Platform.OS === "web") {
      try {
        if (typeof window !== "undefined") {
          window.localStorage.setItem(key, value);
        }
      } catch {
        // ignore quota or privacy errors
      }
      return;
    }
    SecureStore.setItemAsync(key, value);
  },
  removeItem: (key: string) => {
    if (Platform.OS === "web") {
      try {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(key);
        }
      } catch {
        // ignore
      }
      return;
    }
    SecureStore.deleteItemAsync(key);
  },
};

export const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_ANON_KEY, {
  auth: {
    storage: CrossPlatformStorage as any,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

// Get redirect URL based on platform
const getRedirectUrl = () => {
  if (Platform.OS === "web") {
    return `${window.location.origin}/(auth)/oauth-callback`;
  } else {
    return Linking.createURL("/(auth)/oauth-callback");
  }
};

// Sign in with OAuth provider
export const signInWithOAuth = async (provider: "google" | "apple") => {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: getRedirectUrl(),
    },
  });

  if (error) {
    throw error;
  }

  if (data.url && Platform.OS !== "web") {
    await Linking.openURL(data.url);
  }
};

// Handle OAuth callback
export const handleOAuthCallback = async (url: string) => {
  try {
    const params = new URLSearchParams(url.split("#")[1]);
    const access_token = params.get("access_token");
    const refresh_token = params.get("refresh_token");

    if (!access_token || !refresh_token) {
      throw new Error("Token tidak ditemukan di URL callback");
    }

    const { error } = await supabase.auth.setSession({
      access_token,
      refresh_token,
    });

    if (error) {
      throw error;
    }

    return { success: true };
  } catch (e: any) {
    console.error("Gagal menangani OAuth callback:", e);
    return { success: false, error: e.message };
  }
};
