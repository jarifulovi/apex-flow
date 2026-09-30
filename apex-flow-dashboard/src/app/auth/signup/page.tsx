import type { Metadata } from "next";
import { AuthCard } from "@/features/auth/components/AuthCard";
import { SignupForm } from "@/features/auth/components/SignupForm";

export const metadata: Metadata = {
  title: "Create Account | ApexFlow",
  description: "Create your ApexFlow account and start orchestrating workflows.",
};

export default function SignupPage() {
  return (
    <AuthCard
      title="Create your account"
      subtitle="Start orchestrating workflows with ApexFlow"
      footer={{
        label: "Already have an account?",
        linkText: "Sign in",
        href: "/auth/login",
      }}
    >
      <SignupForm />
    </AuthCard>
  );
}
