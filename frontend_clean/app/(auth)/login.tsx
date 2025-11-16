// Lokasi: app/(auth)/login.tsx

import React, { useState } from "react";
import { View, Text, SafeAreaView, ScrollView, StyleSheet } from "react-native";
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
    <SafeAreaView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
      >
        <View style={styles.logoContainer}>
          <Text style={styles.logo}>X</Text>
        </View>

        <View style={styles.formContainer}>
          <Text style={styles.title}>
            Sign in to X
          </Text>

          <SocialButton
            icon="google"
            text="Sign in as Dian"
            onPress={handleGoogleSignIn}
            isLoading={oauthLoading === "google"}
          />
          <View style={styles.spacing} />
          <SocialButton
            icon="apple"
            text="Sign in with Apple"
            onPress={handleAppleSignIn}
            isLoading={oauthLoading === "apple"}
          />

          <View style={styles.dividerContainer}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          {apiError && !errors.password && (
            <Text style={styles.errorText}>{apiError}</Text>
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
          <View style={styles.spacing} />
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

          <View style={styles.spacing} />
          <Button
            title={isSubmitting ? "Loading..." : "Sign in"}
            variant="primary"
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting || !!oauthLoading}
          />

          <View style={styles.spacing} />
          <Button
            title="Forgot password?"
            variant="outline"
            onPress={() => router.push("/(auth)/forgot-password")}
            disabled={isSubmitting || !!oauthLoading}
          />

          <View style={styles.footer}>
            <Text style={styles.footerText}>
              Don't have an account?{" "}
            </Text>
            <Link href="/(auth)/signup" asChild>
              <Text style={styles.linkText}>
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

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  logo: {
    color: '#ffffff',
    fontSize: 48,
    fontWeight: '800',
  },
  formContainer: {
    width: '100%',
    maxWidth: 448,
    marginHorizontal: 'auto',
  },
  title: {
    color: '#ffffff',
    fontSize: 36,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  spacing: {
    height: 16,
  },
  dividerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 16,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#404040',
  },
  dividerText: {
    color: '#a3a3a3',
    paddingHorizontal: 16,
  },
  errorText: {
    color: '#ef4444',
    textAlign: 'center',
    marginBottom: 16,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 24,
  },
  footerText: {
    color: '#a3a3a3',
    fontSize: 16,
  },
  linkText: {
    color: '#3b82f6',
    fontSize: 16,
  },
});
