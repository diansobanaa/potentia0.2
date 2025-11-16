 
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
            // 2. [ALPHA] Sementara skip backend check, langsung set user dari Supabase
            const supabaseUser = data.session.user;
            setUser({
              id: supabaseUser.id,
              email: supabaseUser.email || "",
              created_at: supabaseUser.created_at || new Date().toISOString(),
            } as User);
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
            // [ALPHA] Langsung set user dari session Supabase
            if (session?.user) {
              setUser({
                id: session.user.id,
                email: session.user.email || "",
                created_at: session.user.created_at || new Date().toISOString(),
              } as User);
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