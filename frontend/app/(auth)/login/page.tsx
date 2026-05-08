"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, LogIn, AlertCircle, Brain, Loader2, Lock, User } from "lucide-react";
import { authApi, ApiError } from "@/lib/authApi";
import { useAuthStore } from "@/lib/authStore";
import { devSkip } from "@/lib/devSkip";

export default function LoginPage() {
  const router = useRouter();
  const { setTokens, setUser, isAuthenticated } = useAuthStore();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) router.replace("/");
  }, [isAuthenticated, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!username.trim() || !password) {
      setError("Please enter your username and password.");
      return;
    }
    setLoading(true);
    try {
      const data = await authApi.login({
        username: username.trim(),
        password,
        remember_me: rememberMe,
        device_info: navigator.userAgent,
      });
      setTokens(data.access_token, data.refresh_token, data.expires_in);
      setUser({
        id: data.user_id,
        username: data.username,
        emailVerified: false,
        phoneVerified: false,
        healthProfileDone: data.health_profile_done,
      });
      try {
        const me = await authApi.getMe();
        setUser({
          id: me.id,
          username: me.username,
          email: me.email,
          phone: me.phone,
          emailVerified: me.email_verified,
          phoneVerified: me.phone_verified,
          healthProfileDone: me.health_profile_done,
        });
        router.replace(me.health_profile_done ? "/" : "/health-profile");
      } catch {
        router.replace(data.health_profile_done ? "/" : "/health-profile");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: "#000000" }}
    >
      {/* Subtle top ambient glow */}
      <div
        className="fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at 50% 0%, rgba(10,132,255,0.07) 0%, transparent 70%)",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.25, 0.1, 0.25, 1] }}
        className="w-full max-w-[400px] relative"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 justify-center mb-10">
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center"
            style={{ background: "rgba(10,132,255,0.18)" }}
          >
            <Brain className="w-5 h-5" style={{ color: "#0A84FF" }} />
          </div>
          <span className="text-[22px] font-bold tracking-tight text-white">
            Anatom<span style={{ color: "#0A84FF" }}>-AI</span>
          </span>
        </div>

        {/* Card */}
        <div
          className="rounded-2xl p-8"
          style={{
            background: "#111113",
            border: "1px solid rgba(84,84,88,0.35)",
            boxShadow: "0 8px 40px rgba(0,0,0,0.70)",
          }}
        >
          <h1 className="text-[26px] font-bold text-white tracking-tight mb-1" style={{ letterSpacing: "-0.025em" }}>
            Welcome back
          </h1>
          <p className="text-sm mb-8" style={{ color: "#8E8E93" }}>
            Sign in to your Anatom-AI account
          </p>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-[13px] font-medium mb-2" style={{ color: "#8E8E93" }}>
                Username
              </label>
              <div className="relative">
                <User
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                  style={{ color: "#48484A" }}
                />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  autoComplete="username"
                  autoFocus
                  aria-label="Username"
                  className="auth-input pl-10"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-[13px] font-medium mb-2" style={{ color: "#8E8E93" }}>
                Password
              </label>
              <div className="relative">
                <Lock
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                  style={{ color: "#48484A" }}
                />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  aria-label="Password"
                  className="auth-input pl-10 pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: "#48484A" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#8E8E93"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#48484A"; }}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember me + Forgot */}
            <div className="flex items-center justify-between pt-0.5">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded"
                  style={{ accentColor: "#0A84FF" }}
                />
                <span className="text-[13px]" style={{ color: "#8E8E93" }}>Remember me</span>
              </label>
              <Link
                href="/forgot-password"
                className="text-[13px] font-medium transition-colors"
                style={{ color: "#0A84FF" }}
              >
                Forgot password?
              </Link>
            </div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center gap-2.5 p-3.5 rounded-xl text-sm"
                  style={{
                    background: "rgba(255,69,58,0.10)",
                    border: "1px solid rgba(255,69,58,0.22)",
                    color: "#FF453A",
                  }}
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl font-semibold text-[15px] text-white flex items-center justify-center gap-2 transition-all duration-200 mt-2"
              style={{
                background: loading ? "rgba(10,132,255,0.60)" : "#0A84FF",
                opacity: loading ? 0.75 : 1,
              }}
              onMouseEnter={(e) => { if (!loading) (e.currentTarget as HTMLButtonElement).style.background = "#0A73E0"; }}
              onMouseLeave={(e) => { if (!loading) (e.currentTarget as HTMLButtonElement).style.background = "#0A84FF"; }}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <LogIn className="w-4 h-4" />
              )}
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px" style={{ background: "rgba(84,84,88,0.30)" }} />
            <span className="text-[11px] font-mono" style={{ color: "#48484A" }}>OR</span>
            <div className="flex-1 h-px" style={{ background: "rgba(84,84,88,0.30)" }} />
          </div>

          {/* DEV BYPASS */}
          <button
            type="button"
            onClick={() => devSkip(router)}
            className="w-full py-2.5 rounded-xl text-[13px] font-medium mb-5 transition-all"
            style={{
              background: "rgba(84,84,88,0.14)",
              border: "1px solid rgba(84,84,88,0.30)",
              color: "#8E8E93",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(84,84,88,0.22)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(84,84,88,0.14)"; }}
          >
            Skip — Continue as Guest (Dev)
          </button>

          <p className="text-center text-[13px]" style={{ color: "#8E8E93" }}>
            Don&apos;t have an account?{" "}
            <Link
              href="/signup"
              className="font-semibold transition-colors"
              style={{ color: "#0A84FF" }}
            >
              Create account
            </Link>
          </p>
        </div>

        <p className="mt-6 text-center text-[11px] font-mono" style={{ color: "#48484A" }}>
          AES-256 encrypted · HIPAA-aligned
        </p>
      </motion.div>
    </div>
  );
}
