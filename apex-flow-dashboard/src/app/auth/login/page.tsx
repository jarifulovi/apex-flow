import type { Metadata } from "next";
import { AuthCard } from "@/features/auth/components/AuthCard";
import { LoginForm } from "@/features/auth/components/LoginForm";

export const metadata: Metadata = {
  title: "Sign In | ApexFlow",
  description: "Sign in to your ApexFlow workflow orchestration dashboard.",
};

export default function LoginPage() {
  return (
    <AuthCard
      title="Welcome back"
      subtitle="Sign in to your ApexFlow dashboard"
      footer={{
        label: "Don't have an account?",
        linkText: "Create one",
        href: "/auth/signup",
      }}
    >
      <LoginForm />
    </AuthCard>
  );
}
