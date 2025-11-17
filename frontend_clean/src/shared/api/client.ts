 // Lokasi: src/shared/api/client.ts

import axios from "axios";
import { supabase } from "./supabase"; // Impor klien Supabase
import { env } from "@/src/shared/config/env"; // Impor env kita

// 1. Buat instansi Axios dasar (fallback aman bila baseURL kosong)
const apiClient = axios.create({
  baseURL: env.API_URL || undefined,
  headers: {
    "Content-Type": "application/json",
  },
});

// 2. Interceptor REQUEST (Mengirim Token)
// Interceptor ini berjalan SEBELUM setiap request dikirim
apiClient.interceptors.request.use(
  async (config) => {
    // Ambil sesi (termasuk access_token) dari Supabase
    const { data } = await supabase.auth.getSession();

    if (data.session?.access_token) {
      // Jika token ada, tambahkan ke header Authorization
      config.headers.Authorization = `Bearer ${data.session.access_token}`;
    }
    return config;
  },
  (error) => {
    // Jika ada error saat membuat request
    return Promise.reject(error);
  }
);

// 3. Interceptor RESPONSE (Menangani Token Kedaluwarsa - Best Practice Poin 5)
// Interceptor ini berjalan SETELAH response diterima
apiClient.interceptors.response.use(
  (response) => {
    // Jika response sukses (2xx), langsung kembalikan
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Periksa apakah error adalah 401 (Unauthorized) dan BUKAN request retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Tandai sebagai retry

      try {
        // Coba refresh sesi menggunakan Supabase
        const { error: refreshError } = await supabase.auth.refreshSession();

        if (refreshError) {
          // Gagal refresh (misal: refresh token tidak valid), paksa logout
          // Kita akan tangani ini di hook auth (Fase 2)
          return Promise.reject(refreshError);
        }

        // Ambil sesi baru (yang sudah di-refresh)
        const { data: newSessionData } = await supabase.auth.getSession();
        
        if (newSessionData.session?.access_token) {
          // Update header di instansi Axios default
          axios.defaults.headers.common["Authorization"] =
            `Bearer ${newSessionData.session.access_token}`;
          
          // Update header di request asli yang gagal
          originalRequest.headers.Authorization =
            `Bearer ${newSessionData.session.access_token}`;

          // Ulangi request asli dengan token baru
          return apiClient(originalRequest);
        }
      } catch (e) {
        return Promise.reject(e);
      }
    }

    // Kembalikan error lain (selain 401)
    return Promise.reject(error);
  }
);

export default apiClient;