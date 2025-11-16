// Lokasi: src/features/auth/validation.ts

import { z } from "zod";

// Skema untuk Login
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, { message: "Email tidak boleh kosong" })
    .email({ message: "Email tidak valid" }),
  password: z
    .string()
    .min(1, { message: "Password tidak boleh kosong" }),
});

// Skema untuk Sign Up
export const signupSchema = z.object({
  email: z
    .string()
    .min(1, { message: "Email tidak boleh kosong" })
    .email({ message: "Format email tidak valid" }),
  password: z
    .string()
    .min(8, { message: "Password minimal harus 8 karakter" }),
});

// --- BARU ---
// Skema untuk Lupa Password
export const forgotPasswordSchema = z.object({
  email: z
    .string()
    .min(1, { message: "Email tidak boleh kosong" })
    .email({ message: "Email tidak valid" }),
});
// --- AKHIR BARU ---

// Ekspor tipe data TypeScript dari skema
export type LoginFormFields = z.infer<typeof loginSchema>;
export type SignUpFormFields = z.infer<typeof signupSchema>;
export type ForgotPasswordFormFields = z.infer<typeof forgotPasswordSchema>; // <-- BARU