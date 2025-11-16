// Lokasi: app/(auth)/login.tsx

import React, { useState } from "react";
import { View, Text, SafeAreaView, ScrollView } from "react-native";
import { useRouter, Link } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema, LoginFormFields } from "@/src/features/auth/validation";

import { Input } from "@/src/shared/ui/Input";
import { Button } from "@/src/shared/ui/Button";
import { SocialButton } from "@/src/features/auth/ui/SocialButton";
import { supabase, signInWithOAuth } from "@/src/shared/api/supabase";

export default function LoginScreen() {
  const router = useRouter();
  const [apiError, setApiError] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState<"google" | "apple" | null>(
    null
  );

  const { control, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<LoginFormFields>({
      resolver: zodResolver(loginSchema),
      defaultValues: { email: "", password: "" },
    });

  const handleGoogleSignIn = async () => {
    setOauthLoading("google");
    setApiError(null);
    try {
      await signInWithOAuth("google");
    } catch (e: any) {
      setApiError(e.message);
    }
  };

  const handleAppleSignIn = async () => {
    setOauthLoading("apple");
    setApiError(null);
    try {
      await signInWithOAuth("apple");
    } catch (e: any) {
      setApiError(e.message);
    }
  };

  const onSubmit = async (data: LoginFormFields) => {
    setApiError(null);
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: data.email,
        password: data.password,
      });
      if (error) setApiError("Email atau password tidak valid.");
    } catch (e) {
      setApiError("Terjadi kesalahan. Silakan coba lagi.");
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-black">
      <ScrollView
        className="flex-1"
        contentContainerClassName="flex-grow justify-center p-6"
      >
        <View className="items-center mb-8">
          <Text className="text-white text-5xl font-extrabold">X</Text>
        </View>

        <View className="w-full max-w-md mx-auto space-y-6">
          <Text className="text-white text-4xl font-bold mb-4">
            Sign in to X
          </Text>

          <SocialButton
            icon="google"
            text="Sign in as Dian"
            onPress={handleGoogleSignIn}
            isLoading={oauthLoading === "google"}
          />
          <SocialButton
            icon="apple"
            text="Sign in with Apple"
            onPress={handleAppleSignIn}
            isLoading={oauthLoading === "apple"}
          />

          <View className="flex-row items-center my-4">
            <View className="flex-1 h-px bg-neutral-700" />
            <Text className="text-neutral-400 px-4">or</Text>
            <View className="flex-1 h-px bg-neutral-700" />
          </View>

          {apiError && !errors.password && (
            <Text className="text-red-500 text-center">{apiError}</Text>
          )}

          <Controller
            control={control}
            name="email"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                placeholder="Phone, email, or username"
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                error={errors.email?.message}
              />
            )}
          />
          <Controller
            control={control}
            name="password"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                placeholder="Password"
                secureTextEntry
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                error={errors.password?.message}
              />
            )}
          />

          <Button
            title={isSubmitting ? "Loading..." : "Sign in"}
            variant="primary"
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting || !!oauthLoading}
          />

          <Button
            title="Forgot password?"
            variant="outline"
            onPress={() => router.push("/(auth)/forgot-password")}
            disabled={isSubmitting || !!oauthLoading}
          />

          <View className="flex-row justify-center mt-6">
            <Text className="text-neutral-400 text-base">
              Don't have an account?{" "}
            </Text>
            <Link href="/(auth)/signup" asChild>
              <Text className="text-blue-500 text-base active:opacity-70">
                Sign up
              </Text>
            </Link>
          </View>

        </View>
      </ScrollView>
      <StatusBar style="light" />
    </SafeAreaView>
  );
}
