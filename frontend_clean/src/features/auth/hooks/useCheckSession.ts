 
// Lokasi: src/features/auth/hooks/useCheckSession.ts

import { useEffect } from "react";
import { useAuthActions } from "../store";
import { supabase } from "@/src/shared/api/supabase";
import apiClient from "@/src/shared/api/client";
import { components } from "@/src/shared/api/schema";

type User = components["schemas"]["User"];

export const useCheckSession = () => {
  const { setUser, setStatus } = useAuthActions();

  useEffect(() => {
    const checkSession = async () => {
      try {
        // 1. Cek sesi aktif di Supabase (dari SecureStore/localStorage)
        const { data, error } = await supabase.auth.getSession();

        if (error) {
          throw new Error("Gagal mengambil sesi: " + error.message);
        }

        if (data.session) {
          // 2. Jika sesi Supabase ada, validasi ke backend FastAPI kita
          // Klien Axios kita (apiClient) sudah otomatis menyertakan token
          // berkat interceptor yang kita buat di Fase 1.
          try {
            const response = await apiClient.get<User>("/api/v1/auth/me");
            
            // 3. Sukses! Simpan data user dari FastAPI ke store Zustand
            setUser(response.data);

          } catch (apiError) {
            // Sesi Supabase valid, tapi backend FastAPI menolak kita
            // (misal: user dihapus). Logout paksa.
            console.warn("Sesi valid tapi /auth/me gagal:", apiError);
            await supabase.auth.signOut();
            setUser(null);
          }
        } else {
          // 4. Tidak ada sesi Supabase sama sekali
          setUser(null);
        }
      } catch (e) {
        // Error koneksi atau lainnya
        console.error("Error di useCheckSession:", e);
        setStatus("unauthenticated");
      }
    };

    checkSession();

    // 5. Dengarkan perubahan auth (Login/Logout dari tab lain, dll)
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === "SIGNED_IN") {
          // Jika baru login, ambil data /auth/me
          try {
            const response = await apiClient.get<User>("/api/v1/auth/me");
            setUser(response.data);
          } catch (apiError) {
            console.error("Gagal mengambil /auth/me setelah SIGNED_IN:", apiError);
            setUser(null);
          }
        } else if (event === "SIGNED_OUT") {
          // Jika logout, bersihkan store
          setUser(null);
        }
      }
    );

    // Bersihkan listener saat hook unmount
    return () => {
      authListener?.subscription.unsubscribe();
    };
  }, [setUser, setStatus]);
};