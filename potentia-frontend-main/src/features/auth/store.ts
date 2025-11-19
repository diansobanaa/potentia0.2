 
// Lokasi: src/features/auth/store.ts

import { create } from "zustand";
import { components } from "@/src/shared/api/schema"; // Impor tipe User kita

// Definisikan tipe User dari skema API
type User = components["schemas"]["User"];

// Definisikan state dan action untuk store kita
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  status: "idle" | "loading" | "authenticated" | "unauthenticated";
  actions: {
    setUser: (user: User | null) => void;
    setStatus: (
      status: "idle" | "loading" | "authenticated" | "unauthenticated"
    ) => void;
    logout: () => void;
  };
}

// Buat store Zustand
export const useAuthStore = create<AuthState>((set) => ({
  // State Awal
  user: null,
  isAuthenticated: false,
  status: "loading", // Mulai sebagai 'loading' saat aplikasi pertama dimuat

  // Actions (fungsi untuk mengubah state)
  actions: {
    setUser: (user) =>
      set({
        user,
        isAuthenticated: !!user,
        status: user ? "authenticated" : "unauthenticated",
      }),
    setStatus: (status) => set({ status }),
    logout: () =>
      set({
        user: null,
        isAuthenticated: false,
        status: "unauthenticated",
      }),
  },
}));

// Ekspor hook kustom untuk kemudahan penggunaan
export const useAuthUser = () => useAuthStore((state) => state.user);
export const useAuthStatus = () => useAuthStore((state) => state.status);
export const useAuthActions = () => useAuthStore((state) => state.actions);