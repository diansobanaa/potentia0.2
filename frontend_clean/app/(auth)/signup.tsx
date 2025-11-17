// Lokasi: app/(auth)/signup.tsx

import React, { useState } from "react";
import { View, Text, SafeAreaView, ScrollView, StyleSheet } from "react-native";
import { Link, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { signupSchema, SignUpFormFields } from "@/src/features/auth/validation";

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

  const handleGoogleSignUp = async () => {
    console.log("Tombol Google Sign Up diklik");
  };

  const handleAppleSignUp = async () => {
    console.log("Tombol Apple Sign Up diklik");
  };

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
    <SafeAreaView style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
      >
        <View style={styles.logoContainer}>
          <Text style={styles.logo}>Dirga Mahardika</Text>
        </View>
        <View style={styles.formContainer}>
          <Text style={styles.title}>
            Happening now
          </Text>
          <Text style={styles.subtitle}>
            Join today.
          </Text>

          <SocialButton icon="google" text="Sign up with Google" onPress={handleGoogleSignUp} />
          <View style={styles.spacing} />
          <SocialButton icon="apple" text="Sign up with Apple" onPress={handleAppleSignUp} />
          
          <View style={styles.dividerContainer}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

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
                placeholder="Password (minimal 8 karakter)"
                secureTextEntry
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                error={errors.password?.message}
              />
            )}
          />

          <View style={styles.spacing} />
          <Button
            title={isSubmitting ? "Creating..." : "Create account"}
            variant="primary"
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting}
          />
          
          {apiMessage && (
            <Text style={styles.messageText}>{apiMessage}</Text>
          )}

          <Text style={styles.legalText}>
            By signing up, you agree to the...
          </Text>
          
          <View style={styles.signinContainer}>
            <Text style={styles.signinTitle}>
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
  },
  subtitle: {
    color: '#ffffff',
    fontSize: 30,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  spacing: {
    height: 16,
  },
  dividerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 8,
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
  messageText: {
    textAlign: 'center',
    color: '#ffffff',
    marginTop: 16,
  },
  legalText: {
    color: '#737373',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 16,
  },
  signinContainer: {
    width: '100%',
    maxWidth: 448,
    marginHorizontal: 'auto',
    marginTop: 40,
    gap: 16,
  },
  signinTitle: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
  },
});