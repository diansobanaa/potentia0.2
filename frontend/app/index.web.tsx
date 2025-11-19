import React, { useEffect } from "react";
import { Redirect } from "expo-router";
import { useAuthStatus } from "@/src/features/auth/store";

export default function IndexRoute() {
  const status = useAuthStatus();

  // While auth status is loading, render nothing briefly to avoid flicker
  if (status === "loading") return null;

  // Route users to the right entry point
  if (status === "authenticated") {
    return <Redirect href="/(app)/(tabs)/home" />;
  }
  return <Redirect href="/(auth)/login" />;
}
