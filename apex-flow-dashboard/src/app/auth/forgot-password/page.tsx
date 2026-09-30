import type { Metadata } from "next";
import { AuthCard } from "@/features/auth/components/AuthCard";
import { ForgotPasswordForm } from "@/features/auth/components/ForgotPasswordForm";

export const metadata: Metadata = {
  title: "Reset Password | ApexFlow",
  description: "Reset your ApexFlow account password.",
};

export default function ForgotPasswordPage() {
  return (
    <AuthCard
      title="Reset your password"
      subtitle="We'll send a recovery link to your email"
    >
      <ForgotPasswordForm />
    </AuthCard>
  );
}
