"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Eye, EyeOff, Brain, Loader2, AlertCircle,
  CheckCircle2, Mail, Phone, ArrowRight, RefreshCw, Lock, User,
} from "lucide-react";
import { authApi, ApiError } from "@/lib/authApi";
import { useAuthStore } from "@/lib/authStore";
import { PasswordStrengthBar } from "@/components/auth/PasswordStrengthBar";
import { OtpInput } from "@/components/auth/OtpInput";

// ---------------------------------------------------------------------------
// Step types
// ---------------------------------------------------------------------------

type Step = 1 | 2 | 3;

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function StepBar({ current }: { current: Step }) {
  const steps = [
    { n: 1, label: "Account" },
    { n: 2, label: "Verify" },
    { n: 3, label: "Done" },
  ] as const;

  return (
    <div className="flex items-center mb-8">
      {steps.map((s, i) => (
        <div key={s.n} className="flex items-center flex-1 last:flex-none">
          <div className="flex flex-col items-center gap-1 flex-shrink-0">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-[12px] font-bold transition-all duration-300"
              style={
                current > s.n
                  ? { background: "#32D74B", color: "#fff" }
                  : current === s.n
                  ? { background: "#0A84FF", color: "#fff" }
                  : { background: "rgba(84,84,88,0.25)", color: "#636366", border: "1px solid rgba(84,84,88,0.35)" }
              }
            >
              {current > s.n ? <CheckCircle2 className="w-3.5 h-3.5" /> : s.n}
            </div>
            <span
              className="text-[10px] font-medium whitespace-nowrap"
              style={{
                color: current === s.n ? "#0A84FF" : current > s.n ? "#32D74B" : "#48484A",
              }}
            >
              {s.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div
              className="flex-1 h-px mx-2 mt-[-14px] rounded transition-all duration-500"
              style={{ background: current > s.n ? "#32D74B" : "rgba(84,84,88,0.35)" }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 1 — account details
// ---------------------------------------------------------------------------

interface Step1Props {
  onNext: (userId: string, username: string, password: string) => void;
}

function Step1({ onNext }: Step1Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showCpw, setShowCpw] = useState(false);
  const [error, setError] = useState("");
  const [usernameStatus, setUsernameStatus] = useState<"idle" | "checking" | "available" | "taken">("idle");
  const [loading, setLoading] = useState(false);
  const checkTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (username.length < 3) { setUsernameStatus("idle"); return; }
    setUsernameStatus("checking");
    if (checkTimer.current) clearTimeout(checkTimer.current);
    checkTimer.current = setTimeout(async () => {
      try {
        const res = await authApi.checkUsername(username);
        setUsernameStatus(res.available ? "available" : "taken");
      } catch {
        setUsernameStatus("idle");
      }
    }, 500);
    return () => { if (checkTimer.current) clearTimeout(checkTimer.current); };
  }, [username]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (username.length < 3) { setError("Username must be at least 3 characters."); return; }
    if (usernameStatus === "taken") { setError("That username is already taken. Please choose another."); return; }
    if (usernameStatus === "checking") { setError("Still checking username availability. Please wait a moment."); return; }
    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasDigit = /\d/.test(password);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{}|;':",./<>?]/.test(password);
    if (password.length < 8 || !hasUpper || !hasLower || !hasDigit || !hasSpecial) {
      setError("Password doesn't meet all requirements. Check the strength indicator below.");
      return;
    }
    if (password !== confirmPassword) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      const res = await authApi.signup({ username, password });
      onNext(res.user_id, res.username, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign up failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const usernameStatusIcon = () => {
    if (usernameStatus === "checking") return <Loader2 className="w-4 h-4 animate-spin" style={{ color: "#8E8E93" }} />;
    if (usernameStatus === "available") return <CheckCircle2 className="w-4 h-4" style={{ color: "#32D74B" }} />;
    if (usernameStatus === "taken") return <AlertCircle className="w-4 h-4" style={{ color: "#FF453A" }} />;
    return null;
  };

  const pwBorderColor =
    confirmPassword && password !== confirmPassword
      ? "#FF453A"
      : confirmPassword && password === confirmPassword
      ? "#32D74B"
      : undefined;

  const usernameBorderColor =
    usernameStatus === "available" ? "#32D74B" :
    usernameStatus === "taken" ? "#FF453A" : undefined;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {/* Username */}
      <div>
        <label className="block text-[13px] font-medium mb-2" style={{ color: "#8E8E93" }}>Username</label>
        <div className="relative">
          <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: "#48484A" }} />
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/\s/g, ""))}
            placeholder="Choose a unique username"
            autoComplete="username"
            autoFocus
            minLength={3}
            maxLength={32}
            required
            aria-label="Username"
            className="auth-input pl-10 pr-10"
            style={usernameBorderColor ? { borderColor: usernameBorderColor } : undefined}
          />
          <span className="absolute right-3.5 top-1/2 -translate-y-1/2">{usernameStatusIcon()}</span>
        </div>
        {usernameStatus === "taken" && (
          <p className="mt-1.5 text-[12px]" style={{ color: "#FF453A" }}>Username is already taken.</p>
        )}
        {usernameStatus === "available" && (
          <p className="mt-1.5 text-[12px]" style={{ color: "#32D74B" }}>Username is available!</p>
        )}
      </div>

      {/* Password */}
      <div>
        <label className="block text-[13px] font-medium mb-2" style={{ color: "#8E8E93" }}>Password</label>
        <div className="relative">
          <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: "#48484A" }} />
          <input
            type={showPw ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Create a strong password"
            autoComplete="new-password"
            required
            aria-label="Password"
            className="auth-input pl-10 pr-11"
          />
          <button
            type="button"
            onClick={() => setShowPw((v) => !v)}
            aria-label={showPw ? "Hide password" : "Show password"}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 transition-colors"
            style={{ color: "#48484A" }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#8E8E93"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#48484A"; }}
          >
            {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        <PasswordStrengthBar password={password} />
      </div>

      {/* Confirm password */}
      <div>
        <label className="block text-[13px] font-medium mb-2" style={{ color: "#8E8E93" }}>Confirm Password</label>
        <div className="relative">
          <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" style={{ color: "#48484A" }} />
          <input
            type={showCpw ? "text" : "password"}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Repeat your password"
            autoComplete="new-password"
            required
            aria-label="Confirm password"
            className="auth-input pl-10 pr-11"
            style={pwBorderColor ? { borderColor: pwBorderColor } : undefined}
          />
          <button
            type="button"
            onClick={() => setShowCpw((v) => !v)}
            aria-label={showCpw ? "Hide password" : "Show password"}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 transition-colors"
            style={{ color: "#48484A" }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#8E8E93"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#48484A"; }}
          >
            {showCpw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {confirmPassword && password !== confirmPassword && (
          <p className="mt-1.5 text-[12px]" style={{ color: "#FF453A" }}>Passwords do not match.</p>
        )}
      </div>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2.5 p-3.5 rounded-xl text-sm"
            style={{ background: "rgba(255,69,58,0.10)", border: "1px solid rgba(255,69,58,0.22)", color: "#FF453A" }}
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <button
        type="submit"
        disabled={loading || usernameStatus === "taken" || usernameStatus === "checking"}
        className="w-full py-3 px-4 rounded-xl font-semibold text-[15px] text-white flex items-center justify-center gap-2 transition-all duration-200 mt-2 disabled:cursor-not-allowed"
        style={{ background: loading ? "rgba(10,132,255,0.60)" : "#0A84FF", opacity: (loading || usernameStatus === "taken" || usernameStatus === "checking") ? 0.65 : 1 }}
        onMouseEnter={(e) => { if (!loading) (e.currentTarget as HTMLButtonElement).style.background = "#0A73E0"; }}
        onMouseLeave={(e) => { if (!loading) (e.currentTarget as HTMLButtonElement).style.background = "#0A84FF"; }}
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
        {loading ? "Creating account…" : "Continue"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Step 2 — OTP verification
// ---------------------------------------------------------------------------

interface Step2Props {
  userId: string;
  onNext: () => void;
}

function Step2({ userId, onNext }: Step2Props) {
  const [contactType, setContactType] = useState<"email" | "phone">("email");
  const [contactValue, setContactValue] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [devOtp, setDevOtp] = useState<string | null>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  async function handleSendOtp() {
    setError("");
    if (!contactValue.trim()) {
      setError(`Please enter your ${contactType === "email" ? "email address" : "phone number"}.`);
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.sendOtp({
        user_id: userId,
        contact_type: contactType,
        contact_value: contactValue.trim(),
        purpose: "signup",
      });
      setOtpSent(true);
      setCooldown(60);
      setDevOtp(res.dev_otp ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send OTP.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    setError("");
    if (otp.length < 6) { setError("Please enter the 6-digit OTP."); return; }
    setLoading(true);
    try {
      await authApi.verifyOtp({ user_id: userId, otp, purpose: "signup", contact_type: contactType });
      setVerified(true);
      setTimeout(onNext, 1200);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verification failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-[13px]" style={{ color: "#8E8E93" }}>
        Verify at least one contact method to secure your account.
      </p>

      {/* Contact type toggle */}
      <div
        className="flex rounded-xl p-1 gap-1"
        style={{ background: "rgba(28,28,30,0.80)", border: "1px solid rgba(84,84,88,0.35)" }}
      >
        {(["email", "phone"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => { setContactType(t); setOtpSent(false); setOtp(""); setError(""); setDevOtp(null); }}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-[13px] font-medium transition-all"
            style={
              contactType === t
                ? { background: "#0A84FF", color: "#fff" }
                : { color: "#8E8E93" }
            }
          >
            {t === "email" ? <Mail className="w-4 h-4" /> : <Phone className="w-4 h-4" />}
            {t === "email" ? "Email" : "Phone"}
          </button>
        ))}
      </div>

      {/* Contact input */}
      <div>
        <label className="block text-[13px] font-medium mb-2" style={{ color: "#8E8E93" }}>
          {contactType === "email" ? "Email Address" : "Phone Number"}
        </label>
        <div className="flex gap-2">
          <input
            type={contactType === "email" ? "email" : "tel"}
            value={contactValue}
            onChange={(e) => setContactValue(e.target.value)}
            placeholder={contactType === "email" ? "you@example.com" : "+91 9876543210"}
            disabled={otpSent}
            aria-label={contactType === "email" ? "Email" : "Phone number"}
            className="auth-input flex-1 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={handleSendOtp}
            disabled={loading || cooldown > 0 || verified}
            className="px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all flex items-center gap-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: "rgba(255,255,255,0.08)", color: "#8E8E93" }}
          >
            {loading && !otpSent ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : otpSent && cooldown > 0 ? (
              <><RefreshCw className="w-4 h-4" />{cooldown}s</>
            ) : (
              otpSent ? <><RefreshCw className="w-4 h-4" />Resend</> : "Send OTP"
            )}
          </button>
        </div>
      </div>

      {/* DEV OTP hint */}
      {devOtp && !verified && (
        <div
          className="p-3 rounded-xl text-[13px]"
          style={{ background: "rgba(255,159,10,0.10)", border: "1px solid rgba(255,159,10,0.22)", color: "#FF9F0A" }}
        >
          <span className="font-medium">Dev mode:</span> OTP is{" "}
          <span
            className="font-mono font-bold cursor-pointer underline underline-offset-2"
            onClick={() => setOtp(devOtp)}
            title="Click to fill"
          >
            {devOtp}
          </span>
        </div>
      )}

      {/* OTP input */}
      <AnimatePresence>
        {otpSent && !verified && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <p className="text-[13px] text-center" style={{ color: "#8E8E93" }}>
              Enter the 6-digit code sent to your {contactType}
            </p>
            <OtpInput value={otp} onChange={setOtp} disabled={loading || verified} />
            <button
              type="button"
              onClick={handleVerify}
              disabled={loading || otp.length < 6}
              className="w-full py-3 px-4 rounded-xl font-semibold text-[15px] text-white flex items-center justify-center gap-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: "#32D74B" }}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              {loading ? "Verifying…" : "Verify Code"}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {verified && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-3 p-3.5 rounded-xl text-[13px] font-medium"
            style={{ background: "rgba(50,215,75,0.10)", border: "1px solid rgba(50,215,75,0.22)", color: "#32D74B" }}
          >
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            Verified! Completing your account setup…
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2.5 p-3.5 rounded-xl text-[13px]"
            style={{ background: "rgba(255,69,58,0.10)", border: "1px solid rgba(255,69,58,0.22)", color: "#FF453A" }}
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 3 — completion / auto-login
// ---------------------------------------------------------------------------

interface Step3Props {
  userId: string;
  username: string;
  password: string;
}

function Step3({ userId, username, password }: Step3Props) {
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();

  useEffect(() => {
    async function autoLogin() {
      try {
        const data = await authApi.login({ username, password });
        setTokens(data.access_token, data.refresh_token, data.expires_in);
        const me = await authApi.getMe();
        setUser({
          id: me.id, username: me.username,
          email: me.email, phone: me.phone,
          emailVerified: me.email_verified, phoneVerified: me.phone_verified,
          healthProfileDone: me.health_profile_done,
        });
        setTimeout(() => router.replace("/health-profile"), 1800);
      } catch {
        setTimeout(() => router.replace("/login"), 2000);
      }
    }
    autoLogin();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="text-center space-y-5 py-6"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
        className="w-20 h-20 rounded-full flex items-center justify-center mx-auto"
        style={{ background: "rgba(50,215,75,0.18)" }}
      >
        <CheckCircle2 className="w-10 h-10" style={{ color: "#32D74B" }} />
      </motion.div>
      <div>
        <h2 className="text-[22px] font-bold text-white mb-2">Account Created!</h2>
        <p className="text-[13px]" style={{ color: "#8E8E93" }}>
          Welcome to Anatom-AI,{" "}
          <span style={{ color: "#0A84FF" }} className="font-medium">{username}</span>.
          <br />
          Setting up your health profile…
        </p>
      </div>
      <div className="flex justify-center">
        <Loader2 className="w-5 h-5 animate-spin" style={{ color: "#0A84FF" }} />
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main signup page
// ---------------------------------------------------------------------------

export default function SignupPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [step, setStep] = useState<Step>(1);
  const [userId, setUserId] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (isAuthenticated) router.replace("/");
  }, [isAuthenticated, router]);

  function handleStep1Done(uid: string, uname: string, pw: string) {
    setUserId(uid);
    setUsername(uname);
    setPassword(pw);
    setStep(2);
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
        className="w-full max-w-[420px] relative"
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
          <StepBar current={step} />

          {step === 1 && (
            <>
              <h1 className="text-[24px] font-bold text-white tracking-tight mb-1" style={{ letterSpacing: "-0.025em" }}>
                Create your account
              </h1>
              <p className="text-[13px] mb-6" style={{ color: "#8E8E93" }}>
                Choose a username and a strong password
              </p>
            </>
          )}

          {step === 2 && (
            <>
              <h1 className="text-[24px] font-bold text-white tracking-tight mb-1" style={{ letterSpacing: "-0.025em" }}>
                Verify your identity
              </h1>
              <p className="text-[13px] mb-6" style={{ color: "#8E8E93" }}>
                Secure your account with email or phone verification
              </p>
            </>
          )}

          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25 }}
            >
              {step === 1 && <Step1 onNext={handleStep1Done} />}
              {step === 2 && <Step2 userId={userId} onNext={() => setStep(3)} />}
              {step === 3 && <Step3 userId={userId} username={username} password={password} />}
            </motion.div>
          </AnimatePresence>

          {step < 3 && (
            <>
              {/* Divider */}
              <div className="flex items-center gap-3 my-6">
                <div className="flex-1 h-px" style={{ background: "rgba(84,84,88,0.30)" }} />
                <span className="text-[11px] font-mono" style={{ color: "#48484A" }}>OR</span>
                <div className="flex-1 h-px" style={{ background: "rgba(84,84,88,0.30)" }} />
              </div>
              <p className="text-center text-[13px]" style={{ color: "#8E8E93" }}>
                Already have an account?{" "}
                <Link href="/login" className="font-semibold transition-colors" style={{ color: "#0A84FF" }}>
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>

        <p className="mt-6 text-center text-[11px] font-mono" style={{ color: "#48484A" }}>
          AES-256 encrypted · HIPAA-aligned
        </p>
      </motion.div>
    </div>
  );
}
