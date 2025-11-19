// Lokasi: app/(auth)/forgot-password.tsx

import React, { useState } from "react";
import { View, Text, SafeAreaView } from "react-native";
import { useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  forgotPasswordSchema,
  ForgotPasswordFormFields,
} from "@/src/features/auth/validation";

import { Input } from "@/src/shared/ui/Input";
import { Button } from "@/src/shared/ui/Button";
import { supabase } from "@/src/shared/api/supabase";

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  // Integrasi React Hook Form
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormFields>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  // Fungsi onSubmit
  const onSubmit = async (data: ForgotPasswordFormFields) => {
    setMessage(null);
    setIsSuccess(false);
    try {
      // Panggil fungsi reset password Supabase
      const { error } = await supabase.auth.resetPasswordForEmail(data.email, {
        // Tentukan ke mana Supabase harus mengarahkan pengguna
        // setelah mereka mengklik link di email.
        // Kita akan buat halaman ini nanti.
        redirectTo: "exp://127.0.0.1:8081/--/(auth)/reset-password", // Ganti dengan URL deep link Expo Anda
      });

      if (error) {
        setMessage(error.message);
      } else {
        setMessage(
          "Jika email Anda terdaftar, Anda akan menerima link reset password."
        );
        setIsSuccess(true);
      }
    } catch (e) {
      setMessage("Terjadi kesalahan. Silakan coba lagi.");
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-black">
      <View className="flex-1 justify-center p-6">
        <View className="w-full max-w-md mx-auto space-y-6">
          <Text className="text-white text-3xl font-bold mb-4">
            Reset Password
          </Text>
          <Text className="text-neutral-400 text-base mb-4">
            Masukkan email Anda. Kami akan mengirimkan instruksi untuk me-reset
            password Anda.
          </Text>

          {/* Form Input */}
          <Controller
            control={control}
            name="email"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                placeholder="Alamat Email"
                keyboardType="email-address"
                autoCapitalize="none"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                error={errors.email?.message}
              />
            )}
          />

          {/* Tampilkan pesan sukses atau error */}
          {message && (
            <Text
              className={`text-center ${
                isSuccess ? "text-green-500" : "text-red-500"
              }`}
            >
              {message}
            </Text>
          )}

          <Button
            title={isSubmitting ? "Mengirim..." : "Kirim Link Reset"}
            variant="primary"
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting || isSuccess}
          />

          <Button
            title="Kembali ke Login"
            variant="outline"
            onPress={() => router.replace("/(auth)/login")}
          />
        </View>
      </View>
      <StatusBar style="light" />
    </SafeAreaView>
  );
}