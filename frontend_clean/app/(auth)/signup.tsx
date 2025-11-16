// Lokasi: app/(auth)/signup.tsx

import React, { useState } from "react";
import { View, Text, SafeAreaView, ScrollView } from "react-native";
import { Link, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useForm, Controller } from "react-hook-form"; // <-- Impor Hook Form
import { zodResolver } from "@hookform/resolvers/zod"; // <-- Impor Resolver
import { signupSchema, SignUpFormFields } from "@/src/features/auth/validation"; // <-- Impor Skema

import { Input } from "@/src/shared/ui/Input";
import { Button } from "@/src/shared/ui/Button";
import { SocialButton } from "@/src/features/auth/ui/SocialButton";
import { supabase } from "@/src/shared/api/supabase";

export default function SignUpScreen() {
  const router = useRouter();
  const [apiMessage, setApiMessage] = useState<string | null>(null);

  // --- Integrasi React Hook Form ---
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignUpFormFields>({
    resolver: zodResolver(signupSchema), // Gunakan resolver Zod
    defaultValues: {
      email: "",
      password: "",
    },
  });
  // --- Akhir Integrasi ---

  const handleGoogleSignUp = async () => {/* ... (logika sama) ... */};
  const handleAppleSignUp = async () => {/* ... (logika sama) ... */};

  // Fungsi onSubmit sekarang menerima data yang sudah divalidasi
  const onSubmit = async (data: SignUpFormFields) => {
    setApiMessage(null);
    try {
      const { error } = await supabase.auth.signUp({
        email: data.email,
        password: data.password,
      });

      if (error) {
        if (error.message.includes("User already registered")) {
          setApiMessage("Email ini sudah terdaftar. Silakan login.");
        } else {
          setApiMessage(error.message);
        }
      } else {
        setApiMessage(
          "Pendaftaran berhasil! Silakan cek email Anda untuk verifikasi."
        );
      }
    } catch (e) {
      setApiMessage("Terjadi kesalahan. Silakan coba lagi.");
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-black">
      <ScrollView
        className="flex-1"
        contentContainerClassName="flex-grow justify-center p-6"
      >
        {/* (Logo X & Judul... tetap sama) */}
        <View className="items-center mb-8">
          <Text className="text-white text-5xl font-extrabold">X</Text>
        </View>
        <View className="w-full max-w-md mx-auto space-y-6">
          <Text className="text-white text-4xl font-bold">
            Happening now
          </Text>
          <Text className="text-white text-3xl font-bold mb-4">
            Join today.
          </Text>

          {/* (Tombol Sosial & Divider... tetap sama) */}
          <SocialButton icon="google" text="Sign up with Google" onPress={handleGoogleSignUp} />
          <SocialButton icon="apple" text="Sign up with Apple" onPress={handleAppleSignUp} />
          <View className="flex-row items-center my-2">
            <View className="flex-1 h-px bg-neutral-700" />
            <Text className="text-neutral-400 px-4">or</Text>
            <View className="flex-1 h-px bg-neutral-700" />
          </View>

          {/* --- Form Input (Direfaktor dengan Controller) --- */}
          <Controller
            control={control}
            name="email"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                placeholder="Email"
                keyboardType="email-address"
                autoCapitalize="none"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                error={errors.email?.message} // Tampilkan error validasi
              />
            )}
          />
          <Controller
            control={control}
            name="password"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                placeholder="Password (minimal 8 karakter)"
                secureTextEntry
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                error={errors.password?.message} // Tampilkan error validasi
              />
            )}
          />

          <Button
            title={isSubmitting ? "Creating..." : "Create account"}
            variant="primary"
            onPress={handleSubmit(onSubmit)} // Bungkus onSubmit dengan handleSubmit
            disabled={isSubmitting}
          />
          {/* --- Akhir Refaktor Form --- */}
          
          {apiMessage && (
            <Text className="text-center text-white">{apiMessage}</Text>
          )}

          {/* (Teks Legal & Link Sign In... tetap sama) */}
          <Text className="text-neutral-500 text-xs text-center">
            By signing up, you agree to the...
          </Text>
          <View className="w-full max-w-md mx-auto space-y-4 mt-10">
            <Text className="text-white text-xl font-bold">
              Already have an account?
            </Text>
            <Button
              title="Sign in"
              variant="outline"
              onPress={() => router.replace("/(auth)/login")}
            />
          </View>
        </View>
      </ScrollView>
      <StatusBar style="light" />
    </SafeAreaView>
  );
}