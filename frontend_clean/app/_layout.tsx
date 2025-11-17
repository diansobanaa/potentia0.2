 
// Lokasi: app/_layout.tsx

import "react-native-gesture-handler";
import "./global.css";
import { useEffect } from "react";
import { Stack, useRouter, useSegments } from "expo-router";
import { useAuthStatus } from "@/src/features/auth/store";
import { useCheckSession } from "@/src/features/auth/hooks/useCheckSession";
import { SplashScreen } from "expo-router";

// Tampilkan Splash Screen (layar loading) secara default
SplashScreen.preventAutoHideAsync();

export default function RootLayout({ children }: { children?: React.ReactNode }) {
  // 1. Jalankan hook pengecekan sesi
  useCheckSession();

  // 2. Dapatkan status auth dari store Zustand
  const authStatus = useAuthStatus();
  
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    // 3. Logika Navigasi (Auth Guard)
    const inAuthGroup = segments[0] === "(auth)";

    if (authStatus === "loading") {
      // Masih loading, biarkan splash screen terlihat
      return;
    }

    if (authStatus === "authenticated" && !inAuthGroup) {
      // Pengguna sudah login dan TIDAK berada di grup (auth)
      // Sembunyikan splash screen
      SplashScreen.hideAsync();
    }

    if (authStatus === "authenticated" && inAuthGroup) {
      // Pengguna sudah login TAPI masih di halaman auth (login/signup)
      // Pindahkan paksa ke dashboard (halaman utama)
      router.replace("/(app)/(tabs)/home"); // Arahkan ke tab Home di dalam Drawer
      SplashScreen.hideAsync();
    }

    if (authStatus === "unauthenticated") {
      // Pengguna tidak login
      // Pindahkan paksa ke halaman login
      router.replace("/(auth)/login");
      SplashScreen.hideAsync();
    }
  }, [authStatus, segments, router]);

  // Fallback: jika status masih 'loading' lebih dari 2.5 detik, anggap tidak ada sesi (lebih agresif di web)
  useEffect(() => {
    if (authStatus !== 'loading') return;
    const t = setTimeout(() => {
      if (authStatus === 'loading') {
        // Force unauthenticated to unblock UI
        router.replace('/(auth)/login');
        SplashScreen.hideAsync();
      }
    }, 2500);
    return () => clearTimeout(t);
  }, [authStatus, router]);

  // Sembunyikan header default
  return <Stack screenOptions={{ headerShown: false }}>{children}</Stack>;
}