"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain, Loader2, AlertCircle, CheckCircle2,
  ArrowLeft, Eye, EyeOff, RefreshCw,
} from "lucide-react";
import { authApi, ApiError } from "@/lib/authApi";
import { OtpInput } from "@/components/auth/OtpInput";
import { PasswordStrengthBar } from "@/components/auth/PasswordStrengthBar";

type Step = "identify" | "verify" | "reset" | "done";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("identify");

  // Shared state
  const [userId, setUserId] = useState("");
  const [maskedContact, setMaskedContact] = useState("");
  const [contactType, setContactType] = useState("email");
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPw, setShowPw] = useState(false);

  const [identifier, setIdentifier] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  // Step 1: identify user
  async function handleIdentify(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.forgotPassword({ identifier: identifier.trim() });
      setUserId(res.user_id);
      setMaskedContact(res.masked_contact);
      setContactType(res.contact_type);
      setDevOtp(res.dev_otp ?? null);
      setCooldown(60);
      setStep("verify");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResendOtp() {
    setError("");
    setLoading(true);
    try {
      const res = await authApi.forgotPassword({ identifier: identifier.trim() });
      setDevOtp(res.dev_otp ?? null);
      setCooldown(60);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Resend failed.");
    } finally {
      setLoading(false);
    }
  }

  // Step 3: reset password
  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await authApi.resetPassword({ user_id: userId, otp, new_password: newPassword });
      setStep("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reset failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-white">
            Anatom<span className="text-cyan-400"> AI</span>
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-700/60 rounded-2xl p-8 shadow-2xl backdrop-blur-xl">
          <AnimatePresence mode="wait">

            {/* ── Step 1: Identify ── */}
            {step === "identify" && (
              <motion.div key="identify" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                <h1 className="text-2xl font-bold text-white mb-1">Forgot password?</h1>
                <p className="text-slate-400 text-sm mb-7">
                  Enter your username, email, or phone to receive a reset code.
                </p>
                <form onSubmit={handleIdentify} noValidate className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">
                      Username, Email or Phone
                    </label>
                    <input
                      type="text"
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      placeholder="Enter username, email, or phone"
                      autoFocus
                      required
                      aria-label="Identifier"
                      className="w-full px-4 py-3 rounded-xl bg-slate-800/70 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-all"
                    />
                  </div>
                  <AnimatePresence>
                    {error && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                        className="flex items-center gap-2.5 p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
                      </motion.div>
                    )}
                  </AnimatePresence>
                  <button type="submit" disabled={loading}
                    className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 transition-all flex items-center justify-center gap-2">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    {loading ? "Sending code…" : "Send Reset Code"}
                  </button>
                </form>
              </motion.div>
            )}

            {/* ── Step 2: Verify OTP ── */}
            {step === "verify" && (
              <motion.div key="verify" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-5">
                <div>
                  <button onClick={() => setStep("identify")} className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 text-sm mb-4 transition-colors">
                    <ArrowLeft className="w-4 h-4" /> Back
                  </button>
                  <h1 className="text-2xl font-bold text-white mb-1">Enter reset code</h1>
                  <p className="text-slate-400 text-sm">
                    A 6-digit code was sent to <span className="text-cyan-400">{maskedContact}</span>
                  </p>
                </div>

                {devOtp && (
                  <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
                    <span className="font-medium">Dev mode:</span> OTP is{" "}
                    <span className="font-mono font-bold cursor-pointer underline" onClick={() => setOtp(devOtp)} title="Click to fill">
                      {devOtp}
                    </span>
                  </div>
                )}

                <OtpInput value={otp} onChange={setOtp} />

                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Didn&apos;t receive it?</span>
                  <button
                    type="button"
                    onClick={handleResendOtp}
                    disabled={loading || cooldown > 0}
                    className="flex items-center gap-1.5 text-sm text-cyan-400 hover:text-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend"}
                  </button>
                </div>

                <AnimatePresence>
                  {error && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                      className="flex items-center gap-2.5 p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
                    </motion.div>
                  )}
                </AnimatePresence>

                <button
                  type="button"
                  onClick={() => { setError(""); setStep("reset"); }}
                  disabled={otp.length < 6}
                  className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                >
                  Continue
                </button>
              </motion.div>
            )}

            {/* ── Step 3: New password ── */}
            {step === "reset" && (
              <motion.div key="reset" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                <button onClick={() => setStep("verify")} className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 text-sm mb-4 transition-colors">
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>
                <h1 className="text-2xl font-bold text-white mb-1">Set new password</h1>
                <p className="text-slate-400 text-sm mb-6">Choose a password you haven&apos;t used before.</p>
                <form onSubmit={handleReset} noValidate className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">New Password</label>
                    <div className="relative">
                      <input
                        type={showPw ? "text" : "password"}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="New password"
                        autoComplete="new-password"
                        required
                        aria-label="New password"
                        className="w-full px-4 py-3 pr-11 rounded-xl bg-slate-800/70 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-all"
                      />
                      <button type="button" onClick={() => setShowPw(v => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors">
                        {showPw ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                      </button>
                    </div>
                    <PasswordStrengthBar password={newPassword} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm New Password</label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Repeat new password"
                      autoComplete="new-password"
                      required
                      aria-label="Confirm new password"
                      className={`w-full px-4 py-3 rounded-xl bg-slate-800/70 border text-white placeholder-slate-500 focus:outline-none focus:ring-1 transition-all ${
                        confirmPassword && newPassword !== confirmPassword ? "border-red-500" : "border-slate-600 focus:border-cyan-500 focus:ring-cyan-500/30"
                      }`}
                    />
                  </div>
                  <AnimatePresence>
                    {error && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                        className="flex items-center gap-2.5 p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
                      </motion.div>
                    )}
                  </AnimatePresence>
                  <button type="submit" disabled={loading}
                    className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 transition-all flex items-center justify-center gap-2">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    {loading ? "Resetting…" : "Reset Password"}
                  </button>
                </form>
              </motion.div>
            )}

            {/* ── Step 4: Done ── */}
            {step === "done" && (
              <motion.div key="done" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center space-y-5 py-4">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
                  className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center mx-auto shadow-xl shadow-emerald-500/30"
                >
                  <CheckCircle2 className="w-10 h-10 text-white" />
                </motion.div>
                <h2 className="text-2xl font-bold text-white">Password Reset!</h2>
                <p className="text-slate-400 text-sm">
                  Your password has been updated successfully.<br />
                  You can now sign in with your new password.
                </p>
                <button
                  onClick={() => router.push("/login")}
                  className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 transition-all"
                >
                  Sign In
                </button>
              </motion.div>
            )}

          </AnimatePresence>

          {(step === "identify" || step === "verify") && (
            <p className="mt-6 text-center text-sm text-slate-400">
              Remember your password?{" "}
              <Link href="/login" className="text-cyan-400 font-medium hover:text-cyan-300 transition-colors">
                Sign in
              </Link>
            </p>
          )}

        </div>
      </motion.div>
    </div>
  );
}
