import React, { useState, useCallback, memo } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";

const USE_MOCK_AUTH = false;
const AUTH_ENDPOINTS = {
  login: "/api/auth/login",
  signup: "/api/auth/register",
  sendOtp: "/api/auth/send-otp",
  verifyOtp: "/api/auth/verify-otp",
  forgotOtp: "/api/auth/forgot-otp",
  verifyResetOtp: "/api/auth/verify-reset-otp",
  resetPassword: "/api/auth/reset-password",
};

const HISTORY_KEY = "loginHistory";
const BLOCKED_KEY = "blockedUsers";

const appendLoginHistory = (email) => {
  try {
    const now = new Date();
    const safeEmail = String(email || "").toLowerCase();
    const nameFromEmail = safeEmail.split("@")[0] || "User";

    const entry = {
      id: `lh-${now.getTime()}`,
      name: nameFromEmail,
      email: safeEmail,
      role: safeEmail.includes("admin") ? "Admin" : "User",
      date: now.toISOString().slice(0, 10),
      time: now.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      timestamp: now.getTime(),
    };

    const raw = localStorage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    const next = Array.isArray(parsed) ? [entry, ...parsed] : [entry];
    localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
    window.dispatchEvent(new Event("loginHistoryUpdated"));
  } catch (err) {
    console.error("Failed to store login history:", err);
  }
};

export default function AuthApp() {
  const [currentPage, setCurrentPage] = useState("login");

  return currentPage === "login" ? (
    <Login
      onNavigateToSignup={() => setCurrentPage("signup")}
      onNavigateToForgotPassword={() => setCurrentPage("forgot")}
    />
  ) : currentPage === "signup" ? (
    <Signup onNavigateToLogin={() => setCurrentPage("login")} />
  ) : (
    <ForgotPassword onNavigateToLogin={() => setCurrentPage("login")} />
  );
}

// ==================== LOGIN.JSX ====================
function Login({ onNavigateToSignup, onNavigateToForgotPassword }) {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSignIn = useCallback(
    async (event) => {
      event?.preventDefault();
      if (loading) return;
      setError(null);
      const normalizedEmail = email.trim().toLowerCase();
      if (!normalizedEmail || !password.trim()) {
        setError("Please enter both email and password.");
        return;
      }
      try {
        const blocked = JSON.parse(localStorage.getItem(BLOCKED_KEY) || "{}");
        if (blocked[normalizedEmail]) {
          setError("Your account is blocked. Please contact admin.");
          return;
        }
      } catch (err) {
        console.error("Blocked users check failed:", err);
      }
      setLoading(true);
      try {
        if (!USE_MOCK_AUTH) {
          const res = await requestWithRetry(() =>
            requestJson(AUTH_ENDPOINTS.login, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ email: normalizedEmail, password }),
            })
          );
          if (res && res.access_token) {
            localStorage.setItem("kashikart_token", res.access_token);
            if (res.user) {
              localStorage.setItem("profileName", res.user.full_name || "User");
              localStorage.setItem("profileEmail", res.user.email || "");
              localStorage.setItem("is_superuser", JSON.stringify(res.user.is_superuser || false));
              window.dispatchEvent(new Event("profileInfoUpdated"));
            }
          }
        }
        appendLoginHistory(normalizedEmail);
        navigate("/dashboard", { replace: true });
      } catch (err) {
        setError(getErrorMessage(err, "Unable to sign in."));
      } finally {
        setLoading(false);
      }
    },
    [email, loading, navigate, password]
  );

  return (
    <div className="min-h-screen flex">
      {/* LEFT PANEL */}
      <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
        {/* TOP CONTENT */}
        <div>
          {/* LOGO */}
          <div className="flex items-center gap-3 mb-20">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-lg">Tender Intelligence</p>
              <p className="text-sm text-slate-400">
                Automated Monitoring System
              </p>
            </div>
          </div>

          {/* HERO TEXT */}
          <h1 className="text-[42px] font-bold leading-tight mb-6">
            Never miss a <br />
            <span className="text-blue-400">tender opportunity</span> <br />
            again.
          </h1>

          <p className="text-lg text-slate-400 max-w-md mb-14">
            Automated monitoring of 62+ US government websites.
            <br />
            Real-time alerts for keyword-matched opportunities.
          </p>

          {/* STATS */}
          <div className="grid grid-cols-2 gap-5">
            <StatCard title="62+" subtitle="Sources Monitored" />
            <StatCard title="24/7" subtitle="Auto Scanning" />
            <StatCard title="Real-time" subtitle="Notifications" />
            <StatCard title="Smart" subtitle="Keyword Matching" />
          </div>
        </div>

        {/* FOOTER FIXED TO BOTTOM */}
        <p className="absolute bottom-8 text-sm text-slate-400">
          © 2026 Tender Intelligence System. All rights reserved.
        </p>
      </div>

      {/* RIGHT PANEL */}
      <div className="flex w-full lg:w-1/2 items-center justify-center px-6">
        <div className="w-full max-w-md">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-semibold text-slate-900 mb-2">
              Welcome back
            </h2>
            <p className="text-slate-500">
              Sign in to your account to continue
            </p>
          </div>

          {loading && (
            <div className="mb-4 text-sm text-gray-500 flex items-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
              Signing in...
            </div>
          )}
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* EMAIL */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Email address
            </label>
            <input
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* PASSWORD */}
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-slate-700">
                Password
              </label>
              <button
                onClick={onNavigateToForgotPassword}
                className="text-sm text-blue-600 hover:underline"
              >
                Forgot password?
              </button>
            </div>

            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* BUTTON */}
          <button
            type="button"
            disabled={loading}
            onClick={handleSignIn}
            className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-6 disabled:cursor-not-allowed disabled:opacity-70"
          >
            Sign in
          </button>

          <p className="text-center text-sm text-slate-500">
            Don't have an account?{" "}
            <button
              onClick={onNavigateToSignup}
              className="text-blue-600 hover:underline font-medium"
            >
              Sign up
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

// ==================== FORGOT PASSWORD ====================
function ForgotPassword({ onNavigateToLogin }) {
  const [step, setStep] = useState(1); // 1: email, 2: otp, 3: new password
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [generatedOtp, setGeneratedOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendResetOtp = useCallback(async () => {
    setError(null);
    if (!email || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    try {
      if (USE_MOCK_AUTH) {
        const newOtp = Math.floor(100000 + Math.random() * 900000).toString();
        setGeneratedOtp(newOtp);
        setStep(2);
        alert(
          `Your OTP is: ${newOtp} (Demo mode - in production, this would be sent via email)`
        );
        return;
      }

      await requestWithRetry(() =>
        requestJson(AUTH_ENDPOINTS.forgotOtp, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        })
      );
      setStep(2);
    } catch (err) {
      setError(getErrorMessage(err, "Unable to send reset code."));
    } finally {
      setLoading(false);
    }
  }, [email]);

  const handleOtpChange = useCallback(
    (index, value) => {
      if (value.length > 1) value = value.slice(0, 1);
      if (!/^\d*$/.test(value)) return;

      const newOtp = [...otp];
      newOtp[index] = value;
      setOtp(newOtp);

      if (value && index < 5) {
        document.getElementById(`reset-otp-${index + 1}`)?.focus();
      }
    },
    [otp]
  );

  const handleOtpKeyDown = useCallback(
    (index, e) => {
      if (e.key === "Backspace" && !otp[index] && index > 0) {
        document.getElementById(`reset-otp-${index - 1}`)?.focus();
      }
    },
    [otp]
  );

  const verifyResetOtp = useCallback(async () => {
    setError(null);
    const enteredOtp = otp.join("");
    if (USE_MOCK_AUTH) {
      if (enteredOtp === generatedOtp) {
        setStep(3);
      } else {
        setError("Invalid OTP. Please try again.");
      }
      return;
    }

    setLoading(true);
    try {
      await requestWithRetry(() =>
        requestJson(AUTH_ENDPOINTS.verifyResetOtp, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, otp: enteredOtp }),
        })
      );
      setStep(3);
    } catch (err) {
      setError(getErrorMessage(err, "Invalid OTP. Please try again."));
    } finally {
      setLoading(false);
    }
  }, [email, generatedOtp, otp]);

  const handleResetPassword = useCallback(async () => {
    setError(null);
    if (!newPassword || !confirmPassword) {
      setError("Please fill in both password fields.");
      return;
    }
    if (newPassword.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      if (!USE_MOCK_AUTH) {
        await requestWithRetry(() =>
          requestJson(AUTH_ENDPOINTS.resetPassword, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, newPassword }),
          })
        );
      }
      alert(
        "Password reset successfully! Please login with your new password."
      );
      onNavigateToLogin();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to reset password."));
    } finally {
      setLoading(false);
    }
  }, [confirmPassword, email, newPassword, onNavigateToLogin]);

  return (
    <div className="min-h-screen flex">
      {/* LEFT PANEL */}
      <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
        <div>
          {/* LOGO */}
          <div className="flex items-center gap-3 mb-20">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-lg">Tender Intelligence</p>
              <p className="text-sm text-slate-400">
                Automated Monitoring System
              </p>
            </div>
          </div>

          {/* HERO TEXT */}
          <h1 className="text-[42px] font-bold leading-tight mb-6">
            Reset your <br />
            <span className="text-blue-400">password</span> <br />
            securely.
          </h1>

          <p className="text-lg text-slate-400 max-w-md mb-14">
            We'll help you regain access to your account quickly and securely
            through our verification process.
          </p>

          {/* STEPS */}
          <div className="space-y-4">
            <div
              className={`flex items-center gap-3 ${
                step >= 1 ? "text-white" : "text-slate-500"
              }`}
            >
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                  step >= 1 ? "bg-blue-500" : "bg-white/10"
                }`}
              >
                {step > 1 ? (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : (
                  "1"
                )}
              </div>
              <p>Enter your email address</p>
            </div>
            <div
              className={`flex items-center gap-3 ${
                step >= 2 ? "text-white" : "text-slate-500"
              }`}
            >
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                  step >= 2 ? "bg-blue-500" : "bg-white/10"
                }`}
              >
                {step > 2 ? (
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : (
                  "2"
                )}
              </div>
              <p>Verify OTP code</p>
            </div>
            <div
              className={`flex items-center gap-3 ${
                step >= 3 ? "text-white" : "text-slate-500"
              }`}
            >
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                  step >= 3 ? "bg-blue-500" : "bg-white/10"
                }`}
              >
                3
              </div>
              <p>Create new password</p>
            </div>
          </div>
        </div>

        <p className="absolute bottom-8 text-sm text-slate-400">
          © 2026 Tender Intelligence System. All rights reserved.
        </p>
      </div>

      {/* RIGHT PANEL */}
      <div className="flex w-full lg:w-1/2 items-center justify-center px-6">
        <div className="w-full max-w-md">
          {loading && (
            <div className="mb-4 text-sm text-gray-500 flex items-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
              Processing request...
            </div>
          )}
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          {/* STEP 1: EMAIL */}
          {step === 1 && (
            <>
              <div className="text-center mb-10">
                <h2 className="text-3xl font-semibold text-slate-900 mb-2">
                  Forgot password?
                </h2>
                <p className="text-slate-500">
                  No worries, we'll send you reset instructions
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Email address
                </label>
                <input
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                onClick={sendResetOtp}
                className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-6"
              >
                Send reset code
              </button>

              <button
                onClick={onNavigateToLogin}
                className="w-full flex items-center justify-center gap-2 text-slate-600 hover:text-slate-900"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                Back to login
              </button>
            </>
          )}

          {/* STEP 2: OTP */}
          {step === 2 && (
            <>
              <div className="text-center mb-10">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
                  <svg
                    className="w-8 h-8 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <h2 className="text-3xl font-semibold text-slate-900 mb-2">
                  Check your email
                </h2>
                <p className="text-slate-500">
                  We sent a code to
                  <br />
                  <span className="font-medium text-slate-700">{email}</span>
                </p>
              </div>

              <div className="flex gap-2 justify-center mb-6">
                {otp.map((digit, index) => (
                  <input
                    key={index}
                    id={`reset-otp-${index}`}
                    type="text"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(index, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(index, e)}
                    className="w-12 h-14 text-center text-xl font-semibold rounded-lg border-2 border-slate-200 focus:border-blue-500 focus:outline-none text-slate-700"
                  />
                ))}
              </div>

              <button
                onClick={verifyResetOtp}
                className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-4"
              >
                Verify code
              </button>

              <div className="text-center">
                <p className="text-sm text-slate-500 mb-2">
                  Didn't receive the email?
                </p>
                <button
                  onClick={sendResetOtp}
                  className="text-sm text-blue-600 hover:underline font-medium"
                >
                  Click to resend
                </button>
              </div>

              <button
                onClick={() => setStep(1)}
                className="w-full flex items-center justify-center gap-2 text-slate-600 hover:text-slate-900 mt-6"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                Back
              </button>
            </>
          )}

          {/* STEP 3: NEW PASSWORD */}
          {step === 3 && (
            <>
              <div className="text-center mb-10">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
                  <svg
                    className="w-8 h-8 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <h2 className="text-3xl font-semibold text-slate-900 mb-2">
                  Set new password
                </h2>
                <p className="text-slate-500">
                  Your new password must be different from previously used
                  passwords
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  New password
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
                  >
                    {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Must be at least 6 characters
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Confirm password
                </label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
                  >
                    {showConfirmPassword ? (
                      <EyeOff size={18} />
                    ) : (
                      <Eye size={18} />
                    )}
                  </button>
                </div>
              </div>

              <button
                onClick={handleResetPassword}
                className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-6"
              >
                Reset password
              </button>

              <button
                onClick={onNavigateToLogin}
                className="w-full flex items-center justify-center gap-2 text-slate-600 hover:text-slate-900"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                Back to login
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ==================== SIGNUP.JSX ====================

function Signup({ onNavigateToLogin }) {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showSignupSuccess, setShowSignupSuccess] = useState(false);
  // const [showOtpModal, setShowOtpModal] = useState(false);
  // const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  // const [generatedOtp, setGeneratedOtp] = useState("");
  // const [isEmailVerified, setIsEmailVerified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // const sendOtp = async () => {
  //   setError(null);
  //   if (!email || !email.includes('@')) {
  //     setError("Please enter a valid email address.");
  //     return;
  //   }
  //   setLoading(true);
  //   try {
  //     if (USE_MOCK_AUTH) {
  //       const newOtp = Math.floor(100000 + Math.random() * 900000).toString();
  //       setGeneratedOtp(newOtp);
  //       setShowOtpModal(true);
  //       alert(
  //         `Your OTP is: ${newOtp} (Demo mode - in production, this would be sent to your email)`
  //       );
  //       return;
  //     }
  //
  //     await requestWithRetry(() =>
  //       requestJson(AUTH_ENDPOINTS.sendOtp, {
  //         method: "POST",
  //         headers: { "Content-Type": "application/json" },
  //         body: JSON.stringify({ email }),
  //       })
  //     );
  //     setShowOtpModal(true);
  //   } catch (err) {
  //     setError(getErrorMessage(err, "Unable to send verification code."));
  //   } finally {
  //     setLoading(false);
  //   }
  // };
  //
  // const handleOtpChange = (index, value) => {
  //   if (value.length > 1) value = value.slice(0, 1);
  //   if (!/^\d*$/.test(value)) return;
  //
  //   const newOtp = [...otp];
  //   newOtp[index] = value;
  //   setOtp(newOtp);
  //
  //   if (value && index < 5) {
  //     document.getElementById(`otp-${index + 1}`)?.focus();
  //   }
  // };
  //
  // const handleOtpKeyDown = (index, e) => {
  //   if (e.key === "Backspace" && !otp[index] && index > 0) {
  //     document.getElementById(`otp-${index - 1}`)?.focus();
  //   }
  // };
  //
  // const verifyOtp = async () => {
  //   setError(null);
  //   const enteredOtp = otp.join("");
  //   if (USE_MOCK_AUTH) {
  //     if (enteredOtp === generatedOtp) {
  //       setIsEmailVerified(true);
  //       setShowOtpModal(false);
  //       alert("Email verified successfully!");
  //     } else {
  //       setError("Invalid OTP. Please try again.");
  //     }
  //     return;
  //   }
  //
  //   setLoading(true);
  //   try {
  //     await requestWithRetry(() =>
  //       requestJson(AUTH_ENDPOINTS.verifyOtp, {
  //         method: "POST",
  //         headers: { "Content-Type": "application/json" },
  //         body: JSON.stringify({ email, otp: enteredOtp }),
  //       })
  //     );
  //     setIsEmailVerified(true);
  //     setShowOtpModal(false);
  //   } catch (err) {
  //     setError(getErrorMessage(err, "Invalid OTP. Please try again."));
  //   } finally {
  //     setLoading(false);
  //   }
  // };

  const handleCreateAccount = useCallback(async () => {
    setError(null);
    if (!fullName || !email || !password || !confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      if (!USE_MOCK_AUTH) {
        await requestWithRetry(() =>
          requestJson(AUTH_ENDPOINTS.signup, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
body: JSON.stringify({
              email,
              full_name: fullName,
              password,
              confirm_password: confirmPassword,
            }),
          })
        );
      }
      setShowSignupSuccess(true);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to create account."));
    } finally {
      setLoading(false);
    }
  }, [confirmPassword, email, fullName, password]);

  return (
    <div className="min-h-screen flex">
      {/* LEFT PANEL */}
      <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
        {/* TOP CONTENT */}
        <div>
          {/* LOGO */}
          <div className="flex items-center gap-3 mb-20">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-lg">Tender Intelligence</p>
              <p className="text-sm text-slate-400">
                Automated Monitoring System
              </p>
            </div>
          </div>

          {/* HERO TEXT */}
          <h1 className="text-[42px] font-bold leading-tight mb-6">
            Start tracking <br />
            <span className="text-blue-400">opportunities</span> <br />
            today.
          </h1>

          <p className="text-lg text-slate-400 max-w-md mb-14">
            Join thousands of professionals who never miss a tender opportunity
            with our automated monitoring system.
          </p>

          {/* FEATURES */}
          <div className="space-y-4">
            <FeatureItem text="Monitor 62+ websites" />
            <FeatureItem text="Real-time keyword alerts" />
            <FeatureItem text="Power BI analytics integration" />
            <FeatureItem text="Custom notification settings" />
          </div>
        </div>

        {/* FOOTER FIXED TO BOTTOM */}
        <p className="absolute bottom-8 text-sm text-slate-400">
          © 2026 Tender Intelligence System. All rights reserved.
        </p>
      </div>

      {/* RIGHT PANEL */}
      <div className="flex w-full lg:w-1/2 items-center justify-center px-6 py-8">
        <div className="w-full max-w-md">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-slate-900 mb-1">
              Create an account
            </h2>
            <p className="text-sm text-slate-500">
              Get started with your free account
            </p>
          </div>

          {loading && (
            <div className="mb-4 text-sm text-gray-500 flex items-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
              Processing request...
            </div>
          )}
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* FULL NAME */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Full name
            </label>
            <input
              type="text"
              placeholder="John Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* EMAIL */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Email address
            </label>
            <input
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* PASSWORD */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Must be at least 6 characters
            </p>
          </div>

          {/* CONFIRM PASSWORD */}
          <div className="mb-5">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Confirm password
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? "text" : "password"}
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
              >
                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* BUTTON */}
          <button
            onClick={handleCreateAccount}
            className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-5"
          >
            Create account
          </button>

          <p className="text-center text-sm text-slate-500">
            Already have an account?{" "}
            <button
              onClick={onNavigateToLogin}
              className="text-blue-600 hover:underline font-medium"
            >
              Sign in
            </button>
          </p>
        </div>
      </div>

      {/* SIGNUP SUCCESS MODAL */}
      {showSignupSuccess && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
              <svg
                className="w-8 h-8 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h3 className="text-2xl font-semibold text-slate-900 mb-2">
              Account created
            </h3>
            <p className="text-slate-600 text-sm mb-6">
              {/* We have sent you verification link to your email, kindly verify your email to login. */}
              {/* Check your email for a verification link and confirm to log in. */}
              {/* A verification link has been sent to your email. Verify to continue. */}
              We sent a verification link to your email. Please verify to access
              your account.
            </p>
            <button
              onClick={() => {
                setShowSignupSuccess(false);
                onNavigateToLogin();
              }}
              className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition"
            >
              OK
            </button>
          </div>
        </div>
      )}

      {/* OTP MODAL (disabled for now) */}
      {/* {showOtpModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-2xl font-semibold text-slate-900 mb-2">
                Verify Your Email
              </h3>
              <p className="text-slate-500 text-sm">
                Enter the 6-digit code sent to<br />
                <span className="font-medium text-slate-700">{email}</span>
              </p>
            </div>

            <div className="flex gap-2 justify-center mb-6">
              {otp.map((digit, index) => (
                <input
                  key={index}
                  id={`otp-${index}`}
                  type="text"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(index, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(index, e)}
                  className="w-12 h-14 text-center text-xl font-semibold rounded-lg border-2 border-slate-200 focus:border-blue-500 focus:outline-none text-slate-700"
                />
              ))}
            </div>

            <button
              onClick={verifyOtp}
              className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-3"
            >
              Verify OTP
            </button>

            <button
              onClick={() => setShowOtpModal(false)}
              className="w-full rounded-lg border border-slate-200 py-3 font-medium text-slate-700 hover:bg-slate-50 transition"
            >
              Cancel
            </button>

            <div className="text-center mt-4">
              <button
                onClick={sendOtp}
              className="text-sm text-blue-600 hover:underline"
              >
              Resend OTP
              </button>
            </div>
          </div>
        </div>
      )} */}
    </div>
  );
}

// ==================== SHARED COMPONENTS ====================
const StatCard = memo(function StatCard({ title, subtitle }) {
  return (
    <div className="rounded-xl bg-white/5 px-6 py-5 border border-white/5">
      <p className="text-xl font-semibold">{title}</p>
      <p className="text-sm text-slate-400">{subtitle}</p>
    </div>
  );
});

const FeatureItem = memo(function FeatureItem({ text }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
        <svg
          className="w-3 h-3 text-blue-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>
      <p className="text-slate-300">{text}</p>
    </div>
  );
});
// import React, { useState } from "react";
// import { useNavigate } from "react-router-dom";
// import { Eye, EyeOff } from "lucide-react";
// import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";

// const USE_MOCK_AUTH = true;
// const AUTH_ENDPOINTS = {
//   login: "/api/auth/login",
//   signup: "/api/auth/signup",
//   sendOtp: "/api/auth/send-otp",
//   verifyOtp: "/api/auth/verify-otp",
//   forgotOtp: "/api/auth/forgot-otp",
//   verifyResetOtp: "/api/auth/verify-reset-otp",
//   resetPassword: "/api/auth/reset-password",
// };

// export default function AuthApp() {
//   const [currentPage, setCurrentPage] = useState("login");

//   return currentPage === "login" ? (
//     <Login
//       onNavigateToSignup={() => setCurrentPage("signup")}
//       onNavigateToForgotPassword={() => setCurrentPage("forgot")}
//     />
//   ) : currentPage === "signup" ? (
//     <Signup onNavigateToLogin={() => setCurrentPage("login")} />
//   ) : (
//     <ForgotPassword onNavigateToLogin={() => setCurrentPage("login")} />
//   );
// }

// // ==================== LOGIN.JSX ====================
// function Login({ onNavigateToSignup, onNavigateToForgotPassword }) {
//   const navigate = useNavigate();
//   const [showPassword, setShowPassword] = useState(false);
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState(null);

//   const handleSignIn = async (event) => {
//     event?.preventDefault();
//     setError(null);
//     if (!email.trim() || !password.trim()) {
//       setError("Please enter both email and password.");
//       return;
//     }
//     setLoading(true);
//     try {
//       if (!USE_MOCK_AUTH) {
//         await requestWithRetry(() =>
//           requestJson(AUTH_ENDPOINTS.login, {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ email, password }),
//           })
//         );
//       }
//       navigate("/dashboard", { replace: true });
//     } catch (err) {
//       setError(getErrorMessage(err, "Unable to sign in."));
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="min-h-screen flex">
//       {/* LEFT PANEL */}
//       <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
//         {/* TOP CONTENT */}
//         <div>
//           {/* LOGO */}
//           <div className="flex items-center gap-3 mb-20">
//             <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
//               <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
//               </svg>
//             </div>
//             <div>
//               <p className="font-semibold text-lg">Tender Intelligence</p>
//               <p className="text-sm text-slate-400">
//                 Automated Monitoring System
//               </p>
//             </div>
//           </div>

//           {/* HERO TEXT */}
//           <h1 className="text-[42px] font-bold leading-tight mb-6">
//             Never miss a <br />
//             <span className="text-blue-400">tender opportunity</span> <br />
//             again.
//           </h1>

//           <p className="text-lg text-slate-400 max-w-md mb-14">
//             Automated monitoring of 62+ US government websites.
//             <br />
//             Real-time alerts for keyword-matched opportunities.
//           </p>

//           {/* STATS */}
//           <div className="grid grid-cols-2 gap-5">
//             <StatCard title="62+" subtitle="Sources Monitored" />
//             <StatCard title="24/7" subtitle="Auto Scanning" />
//             <StatCard title="Real-time" subtitle="Notifications" />
//             <StatCard title="Smart" subtitle="Keyword Matching" />
//           </div>
//         </div>

//         {/* FOOTER FIXED TO BOTTOM */}
//         <p className="absolute bottom-8 text-sm text-slate-400">
//           © 2026 Tender Intelligence System. All rights reserved.
//         </p>
//       </div>

//       {/* RIGHT PANEL */}
//       <div className="flex w-full lg:w-1/2 items-center justify-center px-6">
//         <div className="w-full max-w-md">
//           <div className="text-center mb-10">
//             <h2 className="text-3xl font-semibold text-slate-900 mb-2">
//               Welcome back
//             </h2>
//             <p className="text-slate-500">
//               Sign in to your account to continue
//             </p>
//           </div>

//           {loading && (
//             <div className="mb-4 text-sm text-gray-500 flex items-center gap-2">
//               <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
//               Signing in...
//             </div>
//           )}
//           {error && (
//             <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
//               {error}
//             </div>
//           )}

//           {/* EMAIL */}
//           <div className="mb-6">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Email address
//             </label>
//             <input
//               type="email"
//               placeholder="you@company.com"
//               value={email}
//               onChange={(e) => setEmail(e.target.value)}
//               className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//             />
//           </div>

//           {/* PASSWORD */}
//           <div className="mb-4">
//             <div className="flex justify-between items-center mb-2">
//               <label className="block text-sm font-medium text-slate-700">
//                 Password
//               </label>
//               <button
//                 onClick={onNavigateToForgotPassword}
//                 className="text-sm text-blue-600 hover:underline"
//               >
//                 Forgot password?
//               </button>
//             </div>

//             <div className="relative">
//               <input
//                 type={showPassword ? "text" : "password"}
//                 placeholder="••••••••"
//                 value={password}
//                 onChange={(e) => setPassword(e.target.value)}
//                 className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//               />
//               <button
//                 type="button"
//                 onClick={() => setShowPassword(!showPassword)}
//                 className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//               >
//                 {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//               </button>
//             </div>
//           </div>

//           {/* BUTTON */}
//           <button
//             type="button"
//             onClick={handleSignIn}
//             className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-6"
//           >
//             Sign in
//           </button>

//           <p className="text-center text-sm text-slate-500">
//             Don't have an account?{" "}
//             <button
//               onClick={onNavigateToSignup}
//               className="text-blue-600 hover:underline font-medium"
//             >
//               Sign up
//             </button>
//           </p>
//         </div>
//       </div>
//     </div>
//   );
// }

// // ==================== FORGOT PASSWORD ====================
// function ForgotPassword({ onNavigateToLogin }) {
//   const [step, setStep] = useState(1); // 1: email, 2: otp, 3: new password
//   const [email, setEmail] = useState("");
//   const [otp, setOtp] = useState(["", "", "", "", "", ""]);
//   const [generatedOtp, setGeneratedOtp] = useState("");
//   const [newPassword, setNewPassword] = useState("");
//   const [confirmPassword, setConfirmPassword] = useState("");
//   const [showNewPassword, setShowNewPassword] = useState(false);
//   const [showConfirmPassword, setShowConfirmPassword] = useState(false);
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState(null);

//   const sendResetOtp = async () => {
//     setError(null);
//     if (!email || !email.includes("@")) {
//       setError("Please enter a valid email address.");
//       return;
//     }
//     setLoading(true);
//     try {
//       if (USE_MOCK_AUTH) {
//         const newOtp = Math.floor(100000 + Math.random() * 900000).toString();
//         setGeneratedOtp(newOtp);
//         setStep(2);
//         alert(
//           `Your OTP is: ${newOtp} (Demo mode - in production, this would be sent via email)`
//         );
//         return;
//       }

//       await requestWithRetry(() =>
//         requestJson(AUTH_ENDPOINTS.forgotOtp, {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify({ email }),
//         })
//       );
//       setStep(2);
//     } catch (err) {
//       setError(getErrorMessage(err, "Unable to send reset code."));
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleOtpChange = (index, value) => {
//     if (value.length > 1) value = value.slice(0, 1);
//     if (!/^\d*$/.test(value)) return;

//     const newOtp = [...otp];
//     newOtp[index] = value;
//     setOtp(newOtp);

//     if (value && index < 5) {
//       document.getElementById(`reset-otp-${index + 1}`)?.focus();
//     }
//   };

//   const handleOtpKeyDown = (index, e) => {
//     if (e.key === "Backspace" && !otp[index] && index > 0) {
//       document.getElementById(`reset-otp-${index - 1}`)?.focus();
//     }
//   };

//   const verifyResetOtp = async () => {
//     setError(null);
//     const enteredOtp = otp.join("");
//     if (USE_MOCK_AUTH) {
//       if (enteredOtp === generatedOtp) {
//         setStep(3);
//       } else {
//         setError("Invalid OTP. Please try again.");
//       }
//       return;
//     }

//     setLoading(true);
//     try {
//       await requestWithRetry(() =>
//         requestJson(AUTH_ENDPOINTS.verifyResetOtp, {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify({ email, otp: enteredOtp }),
//         })
//       );
//       setStep(3);
//     } catch (err) {
//       setError(getErrorMessage(err, "Invalid OTP. Please try again."));
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleResetPassword = async () => {
//     setError(null);
//     if (!newPassword || !confirmPassword) {
//       setError("Please fill in both password fields.");
//       return;
//     }
//     if (newPassword.length < 6) {
//       setError("Password must be at least 6 characters.");
//       return;
//     }
//     if (newPassword !== confirmPassword) {
//       setError("Passwords do not match.");
//       return;
//     }
//     setLoading(true);
//     try {
//       if (!USE_MOCK_AUTH) {
//         await requestWithRetry(() =>
//           requestJson(AUTH_ENDPOINTS.resetPassword, {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ email, newPassword }),
//           })
//         );
//       }
//       alert(
//         "Password reset successfully! Please login with your new password."
//       );
//       onNavigateToLogin();
//     } catch (err) {
//       setError(getErrorMessage(err, "Failed to reset password."));
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="min-h-screen flex">
//       {/* LEFT PANEL */}
//       <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
//         <div>
//           {/* LOGO */}
//           <div className="flex items-center gap-3 mb-20">
//             <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
//               <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
//               </svg>
//             </div>
//             <div>
//               <p className="font-semibold text-lg">Tender Intelligence</p>
//               <p className="text-sm text-slate-400">
//                 Automated Monitoring System
//               </p>
//             </div>
//           </div>

//           {/* HERO TEXT */}
//           <h1 className="text-[42px] font-bold leading-tight mb-6">
//             Reset your <br />
//             <span className="text-blue-400">password</span> <br />
//             securely.
//           </h1>

//           <p className="text-lg text-slate-400 max-w-md mb-14">
//             We'll help you regain access to your account quickly and securely through our verification process.
//           </p>

//           {/* STEPS */}
//           <div className="space-y-4">
//             <div className={`flex items-center gap-3 ${step >= 1 ? 'text-white' : 'text-slate-500'}`}>
//               <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${step >= 1 ? 'bg-blue-500' : 'bg-white/10'}`}>
//                 {step > 1 ? (
//                   <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//                   </svg>
//                 ) : '1'}
//               </div>
//               <p>Enter your email address</p>
//             </div>
//             <div className={`flex items-center gap-3 ${step >= 2 ? 'text-white' : 'text-slate-500'}`}>
//               <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${step >= 2 ? 'bg-blue-500' : 'bg-white/10'}`}>
//                 {step > 2 ? (
//                   <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//                   </svg>
//                 ) : '2'}
//               </div>
//               <p>Verify OTP code</p>
//             </div>
//             <div className={`flex items-center gap-3 ${step >= 3 ? 'text-white' : 'text-slate-500'}`}>
//               <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${step >= 3 ? 'bg-blue-500' : 'bg-white/10'}`}>
//                 3
//               </div>
//               <p>Create new password</p>
//             </div>
//           </div>
//         </div>

//         <p className="absolute bottom-8 text-sm text-slate-400">
//           © 2026 Tender Intelligence System. All rights reserved.
//         </p>
//       </div>

//       {/* RIGHT PANEL */}
//       <div className="flex w-full lg:w-1/2 items-center justify-center px-6">
//         <div className="w-full max-w-md">
//           {loading && (
//             <div className="mb-4 text-sm text-gray-500 flex items-center gap-2">
//               <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
//               Processing request...
//             </div>
//           )}
//           {error && (
//             <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
//               {error}
//             </div>
//           )}
//           {/* STEP 1: EMAIL */}
//           {step === 1 && (
//             <>
//               <div className="text-center mb-10">
//                 <h2 className="text-3xl font-semibold text-slate-900 mb-2">
//                   Forgot password?
//                 </h2>
//                 <p className="text-slate-500">
//                   No worries, we'll send you reset instructions
//                 </p>
//               </div>

//               <div className="mb-6">
//                 <label className="block text-sm font-medium text-slate-700 mb-2">
//                   Email address
//                 </label>
//                 <input
//                   type="email"
//                   placeholder="you@company.com"
//                   value={email}
//                   onChange={(e) => setEmail(e.target.value)}
//                   className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//                 />
//               </div>

//               <button
//                 onClick={sendResetOtp}
//                 className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-6"
//               >
//                 Send reset code
//               </button>

//               <button
//                 onClick={onNavigateToLogin}
//                 className="w-full flex items-center justify-center gap-2 text-slate-600 hover:text-slate-900"
//               >
//                 <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
//                 </svg>
//                 Back to login
//               </button>
//             </>
//           )}

//           {/* STEP 2: OTP */}
//           {step === 2 && (
//             <>
//               <div className="text-center mb-10">
//                 <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
//                   <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
//                   </svg>
//                 </div>
//                 <h2 className="text-3xl font-semibold text-slate-900 mb-2">
//                   Check your email
//                 </h2>
//                 <p className="text-slate-500">
//                   We sent a code to<br />
//                   <span className="font-medium text-slate-700">{email}</span>
//                 </p>
//               </div>

//               <div className="flex gap-2 justify-center mb-6">
//                 {otp.map((digit, index) => (
//                   <input
//                     key={index}
//                     id={`reset-otp-${index}`}
//                     type="text"
//                     maxLength={1}
//                     value={digit}
//                     onChange={(e) => handleOtpChange(index, e.target.value)}
//                     onKeyDown={(e) => handleOtpKeyDown(index, e)}
//                     className="w-12 h-14 text-center text-xl font-semibold rounded-lg border-2 border-slate-200 focus:border-blue-500 focus:outline-none text-slate-700"
//                   />
//                 ))}
//               </div>

//               <button
//                 onClick={verifyResetOtp}
//                 className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-4"
//               >
//                 Verify code
//               </button>

//               <div className="text-center">
//                 <p className="text-sm text-slate-500 mb-2">
//                   Didn't receive the email?
//                 </p>
//                 <button
//                   onClick={sendResetOtp}
//                   className="text-sm text-blue-600 hover:underline font-medium"
//                 >
//                   Click to resend
//                 </button>
//               </div>

//               <button
//                 onClick={() => setStep(1)}
//                 className="w-full flex items-center justify-center gap-2 text-slate-600 hover:text-slate-900 mt-6"
//               >
//                 <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
//                 </svg>
//                 Back
//               </button>
//             </>
//           )}

//           {/* STEP 3: NEW PASSWORD */}
//           {step === 3 && (
//             <>
//               <div className="text-center mb-10">
//                 <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
//                   <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//                   </svg>
//                 </div>
//                 <h2 className="text-3xl font-semibold text-slate-900 mb-2">
//                   Set new password
//                 </h2>
//                 <p className="text-slate-500">
//                   Your new password must be different from previously used passwords
//                 </p>
//               </div>

//               <div className="mb-4">
//                 <label className="block text-sm font-medium text-slate-700 mb-2">
//                   New password
//                 </label>
//                 <div className="relative">
//                   <input
//                     type={showNewPassword ? "text" : "password"}
//                     placeholder="••••••••"
//                     value={newPassword}
//                     onChange={(e) => setNewPassword(e.target.value)}
//                     className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//                   />
//                   <button
//                     type="button"
//                     onClick={() => setShowNewPassword(!showNewPassword)}
//                     className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//                   >
//                     {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//                   </button>
//                 </div>
//                 <p className="text-xs text-slate-500 mt-1">Must be at least 6 characters</p>
//               </div>

//               <div className="mb-6">
//                 <label className="block text-sm font-medium text-slate-700 mb-2">
//                   Confirm password
//                 </label>
//                 <div className="relative">
//                   <input
//                     type={showConfirmPassword ? "text" : "password"}
//                     placeholder="••••••••"
//                     value={confirmPassword}
//                     onChange={(e) => setConfirmPassword(e.target.value)}
//                     className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//                   />
//                   <button
//                     type="button"
//                     onClick={() => setShowConfirmPassword(!showConfirmPassword)}
//                     className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//                   >
//                     {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//                   </button>
//                 </div>
//               </div>

//               <button
//                 onClick={handleResetPassword}
//                 className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-6"
//               >
//                 Reset password
//               </button>

//               <button
//                 onClick={onNavigateToLogin}
//                 className="w-full flex items-center justify-center gap-2 text-slate-600 hover:text-slate-900"
//               >
//                 <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
//                 </svg>
//                 Back to login
//               </button>
//             </>
//           )}
//         </div>
//       </div>
//     </div>
//   );
// }

// // ==================== SIGNUP.JSX ====================

// function Signup({ onNavigateToLogin }) {
//   const [showPassword, setShowPassword] = useState(false);
//   const [showConfirmPassword, setShowConfirmPassword] = useState(false);
//   const [fullName, setFullName] = useState("");
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");
//   const [confirmPassword, setConfirmPassword] = useState("");
//   const [showOtpModal, setShowOtpModal] = useState(false);
//   const [otp, setOtp] = useState(["", "", "", "", "", ""]);
//   const [generatedOtp, setGeneratedOtp] = useState("");
//   const [isEmailVerified, setIsEmailVerified] = useState(false);
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState(null);

//   const sendOtp = async () => {
//     setError(null);
//     if (!email || !email.includes('@')) {
//       setError("Please enter a valid email address.");
//       return;
//     }
//     setLoading(true);
//     try {
//       if (USE_MOCK_AUTH) {
//         const newOtp = Math.floor(100000 + Math.random() * 900000).toString();
//         setGeneratedOtp(newOtp);
//         setShowOtpModal(true);
//         alert(
//           `Your OTP is: ${newOtp} (Demo mode - in production, this would be sent to your email)`
//         );
//         return;
//       }

//       await requestWithRetry(() =>
//         requestJson(AUTH_ENDPOINTS.sendOtp, {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify({ email }),
//         })
//       );
//       setShowOtpModal(true);
//     } catch (err) {
//       setError(getErrorMessage(err, "Unable to send verification code."));
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleOtpChange = (index, value) => {
//     if (value.length > 1) value = value.slice(0, 1);
//     if (!/^\d*$/.test(value)) return;

//     const newOtp = [...otp];
//     newOtp[index] = value;
//     setOtp(newOtp);

//     if (value && index < 5) {
//       document.getElementById(`otp-${index + 1}`)?.focus();
//     }
//   };

//   const handleOtpKeyDown = (index, e) => {
//     if (e.key === "Backspace" && !otp[index] && index > 0) {
//       document.getElementById(`otp-${index - 1}`)?.focus();
//     }
//   };

//   const verifyOtp = async () => {
//     setError(null);
//     const enteredOtp = otp.join("");
//     if (USE_MOCK_AUTH) {
//       if (enteredOtp === generatedOtp) {
//         setIsEmailVerified(true);
//         setShowOtpModal(false);
//         alert("Email verified successfully!");
//       } else {
//         setError("Invalid OTP. Please try again.");
//       }
//       return;
//     }

//     setLoading(true);
//     try {
//       await requestWithRetry(() =>
//         requestJson(AUTH_ENDPOINTS.verifyOtp, {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify({ email, otp: enteredOtp }),
//         })
//       );
//       setIsEmailVerified(true);
//       setShowOtpModal(false);
//     } catch (err) {
//       setError(getErrorMessage(err, "Invalid OTP. Please try again."));
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleCreateAccount = async () => {
//     setError(null);
//     if (!fullName || !email || !password || !confirmPassword) {
//       setError("Please fill in all fields.");
//       return;
//     }
//     if (!isEmailVerified) {
//       setError("Please verify your email first.");
//       return;
//     }
//     if (password.length < 6) {
//       setError("Password must be at least 6 characters.");
//       return;
//     }
//     if (password !== confirmPassword) {
//       setError("Passwords do not match.");
//       return;
//     }
//     setLoading(true);
//     try {
//       if (!USE_MOCK_AUTH) {
//         await requestWithRetry(() =>
//           requestJson(AUTH_ENDPOINTS.signup, {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({
//               fullName,
//               email,
//               password,
//             }),
//           })
//         );
//       }
//       alert("Account created successfully! (Demo mode)");
//       onNavigateToLogin();
//     } catch (err) {
//       setError(getErrorMessage(err, "Failed to create account."));
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="min-h-screen flex">
//       {/* LEFT PANEL */}
//       <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
//         {/* TOP CONTENT */}
//         <div>
//           {/* LOGO */}
//           <div className="flex items-center gap-3 mb-20">
//             <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
//               <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
//               </svg>
//             </div>
//             <div>
//               <p className="font-semibold text-lg">Tender Intelligence</p>
//               <p className="text-sm text-slate-400">
//                 Automated Monitoring System
//               </p>
//             </div>
//           </div>

//           {/* HERO TEXT */}
//           <h1 className="text-[42px] font-bold leading-tight mb-6">
//             Start tracking <br />
//             <span className="text-blue-400">opportunities</span> <br />
//             today.
//           </h1>

//           <p className="text-lg text-slate-400 max-w-md mb-14">
//             Join thousands of professionals who never miss a tender opportunity with our automated monitoring system.
//           </p>

//           {/* FEATURES */}
//           <div className="space-y-4">
//             <FeatureItem text="Monitor 62+ websites" />
//             <FeatureItem text="Real-time keyword alerts" />
//             <FeatureItem text="Power BI analytics integration" />
//             <FeatureItem text="Custom notification settings" />
//           </div>
//         </div>

//         {/* FOOTER FIXED TO BOTTOM */}
//         <p className="absolute bottom-8 text-sm text-slate-400">
//           © 2026 Tender Intelligence System. All rights reserved.
//         </p>
//       </div>

//       {/* RIGHT PANEL */}
//       <div className="flex w-full lg:w-1/2 items-center justify-center px-6 py-8">
//         <div className="w-full max-w-md">
//           <div className="text-center mb-6">
//             <h2 className="text-2xl font-semibold text-slate-900 mb-1">
//               Create an account
//             </h2>
//             <p className="text-sm text-slate-500">
//               Get started with your free account
//             </p>
//           </div>

//           {loading && (
//             <div className="mb-4 text-sm text-gray-500 flex items-center gap-2">
//               <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
//               Processing request...
//             </div>
//           )}
//           {error && (
//             <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
//               {error}
//             </div>
//           )}

//           {/* FULL NAME */}
//           <div className="mb-4">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Full name
//             </label>
//             <input
//               type="text"
//               placeholder="John Doe"
//               value={fullName}
//               onChange={(e) => setFullName(e.target.value)}
//               className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//             />
//           </div>

//           {/* EMAIL WITH VERIFICATION */}
//           <div className="mb-4">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Email address
//             </label>
//             <div className="flex gap-2">
//               <input
//                 type="email"
//                 placeholder="you@company.com"
//                 value={email}
//                 onChange={(e) => setEmail(e.target.value)}
//                 disabled={isEmailVerified}
//                 className={`flex-1 rounded-lg border px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
//                   isEmailVerified ? 'bg-slate-50 border-green-300' : 'border-slate-200'
//                 }`}
//               />
//               {!isEmailVerified ? (
//                 <button
//                   type="button"
//                   onClick={sendOtp}
//                   className="px-5 py-3 rounded-lg bg-blue-500 text-white font-medium hover:bg-blue-600 transition whitespace-nowrap"
//                 >
//                   Verify
//                 </button>
//               ) : (
//                 <div className="flex items-center px-4 py-3 rounded-lg bg-green-50 border border-green-300">
//                   <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//                   </svg>
//                 </div>
//               )}
//             </div>
//             {isEmailVerified && (
//               <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
//                 <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//                 </svg>
//                 Email verified
//               </p>
//             )}
//           </div>

//           {/* PASSWORD */}
//           <div className="mb-4">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Password
//             </label>
//             <div className="relative">
//               <input
//                 type={showPassword ? "text" : "password"}
//                 placeholder="••••••••"
//                 value={password}
//                 onChange={(e) => setPassword(e.target.value)}
//                 className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//               />
//               <button
//                 type="button"
//                 onClick={() => setShowPassword(!showPassword)}
//                 className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//               >
//                 {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//               </button>
//             </div>
//             <p className="text-xs text-slate-500 mt-1">Must be at least 6 characters</p>
//           </div>

//           {/* CONFIRM PASSWORD */}
//           <div className="mb-5">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Confirm password
//             </label>
//             <div className="relative">
//               <input
//                 type={showConfirmPassword ? "text" : "password"}
//                 placeholder="••••••••"
//                 value={confirmPassword}
//                 onChange={(e) => setConfirmPassword(e.target.value)}
//                 className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//               />
//               <button
//                 type="button"
//                 onClick={() => setShowConfirmPassword(!showConfirmPassword)}
//                 className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//               >
//                 {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//               </button>
//             </div>
//           </div>

//           {/* BUTTON */}
//           <button
//             onClick={handleCreateAccount}
//             className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-5"
//           >
//             Create account
//           </button>

//           <p className="text-center text-sm text-slate-500">
//             Already have an account?{" "}
//             <button
//               onClick={onNavigateToLogin}
//               className="text-blue-600 hover:underline font-medium"
//             >
//               Sign in
//             </button>
//           </p>
//         </div>
//       </div>

//       {/* OTP MODAL */}
//       {showOtpModal && (
//         <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
//           <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
//             <div className="text-center mb-6">
//               <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
//                 <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
//                 </svg>
//               </div>
//               <h3 className="text-2xl font-semibold text-slate-900 mb-2">
//                 Verify Your Email
//               </h3>
//               <p className="text-slate-500 text-sm">
//                 Enter the 6-digit code sent to<br />
//                 <span className="font-medium text-slate-700">{email}</span>
//               </p>
//             </div>

//             <div className="flex gap-2 justify-center mb-6">
//               {otp.map((digit, index) => (
//                 <input
//                   key={index}
//                   id={`otp-${index}`}
//                   type="text"
//                   maxLength={1}
//                   value={digit}
//                   onChange={(e) => handleOtpChange(index, e.target.value)}
//                   onKeyDown={(e) => handleOtpKeyDown(index, e)}
//                   className="w-12 h-14 text-center text-xl font-semibold rounded-lg border-2 border-slate-200 focus:border-blue-500 focus:outline-none text-slate-700"
//                 />
//               ))}
//             </div>

//             <button
//               onClick={verifyOtp}
//               className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-3"
//             >
//               Verify OTP
//             </button>

//             <button
//               onClick={() => setShowOtpModal(false)}
//               className="w-full rounded-lg border border-slate-200 py-3 font-medium text-slate-700 hover:bg-slate-50 transition"
//             >
//               Cancel
//             </button>

//             <div className="text-center mt-4">
//               <button
//                 onClick={sendOtp}
//               className="text-sm text-blue-600 hover:underline"
//               >
//               Resend OTP
//               </button>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// // ==================== SHARED COMPONENTS ====================
// function StatCard({ title, subtitle }) {
//   return (
//     <div className="rounded-xl bg-white/5 px-6 py-5 border border-white/5">
//       <p className="text-xl font-semibold">{title}</p>
//       <p className="text-sm text-slate-400">{subtitle}</p>
//     </div>
//   );
// }

// function FeatureItem({ text }) {
//   return (
//     <div className="flex items-center gap-3">
//       <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
//         <svg className="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//         </svg>
//       </div>
//       <p className="text-slate-300">{text}</p>
//     </div>
//   );
// }

// import React, { useState } from "react";
// import { Eye, EyeOff } from "lucide-react";

// export default function AuthApp() {
//   const [currentPage, setCurrentPage] = useState("login");

//   return currentPage === "login" ? (
//     <Login onNavigateToSignup={() => setCurrentPage("signup")} />
//   ) : (
//     <Signup onNavigateToLogin={() => setCurrentPage("login")} />
//   );
// }

// // ==================== LOGIN.JSX ====================
// function Login({ onNavigateToSignup }) {
//   const [showPassword, setShowPassword] = useState(false);
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");

//   const handleSignIn = () => {
//     if (email && password) {
//       alert("Sign in successful! (Demo mode)");
//     } else {
//       alert("Please enter both email and password");
//     }
//   };

//   return (
//     <div className="min-h-screen flex">
//       {/* LEFT PANEL */}
//       <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
//         {/* TOP CONTENT */}
//         <div>
//           {/* LOGO */}
//           <div className="flex items-center gap-3 mb-20">
//             <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
//               <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
//               </svg>
//             </div>
//             <div>
//               <p className="font-semibold text-lg">Tender Intelligence</p>
//               <p className="text-sm text-slate-400">
//                 Automated Monitoring System
//               </p>
//             </div>
//           </div>

//           {/* HERO TEXT */}
//           <h1 className="text-[42px] font-bold leading-tight mb-6">
//             Never miss a <br />
//             <span className="text-blue-400">tender opportunity</span> <br />
//             again.
//           </h1>

//           <p className="text-lg text-slate-400 max-w-md mb-14">
//             Automated monitoring of 62+ US government websites.
//             <br />
//             Real-time alerts for keyword-matched opportunities.
//           </p>

//           {/* STATS */}
//           <div className="grid grid-cols-2 gap-5">
//             <StatCard title="62+" subtitle="Sources Monitored" />
//             <StatCard title="24/7" subtitle="Auto Scanning" />
//             <StatCard title="Real-time" subtitle="Notifications" />
//             <StatCard title="Smart" subtitle="Keyword Matching" />
//           </div>
//         </div>

//         {/* FOOTER FIXED TO BOTTOM */}
//         <p className="absolute bottom-8 text-sm text-slate-400">
//           © 2026 Tender Intelligence System. All rights reserved.
//         </p>
//       </div>

//       {/* RIGHT PANEL */}
//       <div className="flex w-full lg:w-1/2 items-center justify-center px-6">
//         <div className="w-full max-w-md">
//           <div className="text-center mb-10">
//             <h2 className="text-3xl font-semibold text-slate-900 mb-2">
//               Welcome back
//             </h2>
//             <p className="text-slate-500">
//               Sign in to your account to continue
//             </p>
//           </div>

//           {/* EMAIL */}
//           <div className="mb-6">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Email address
//             </label>
//             <input
//               type="email"
//               placeholder="you@company.com"
//               value={email}
//               onChange={(e) => setEmail(e.target.value)}
//               className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//             />
//           </div>

//           {/* PASSWORD */}
//           <div className="mb-4">
//             <div className="flex justify-between items-center mb-2">
//               <label className="block text-sm font-medium text-slate-700">
//                 Password
//               </label>
//               <button className="text-sm text-blue-600 hover:underline">
//                 Forgot password?
//               </button>
//             </div>

//             <div className="relative">
//               <input
//                 type={showPassword ? "text" : "password"}
//                 placeholder="••••••••"
//                 value={password}
//                 onChange={(e) => setPassword(e.target.value)}
//                 className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//               />
//               <button
//                 type="button"
//                 onClick={() => setShowPassword(!showPassword)}
//                 className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//               >
//                 {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//               </button>
//             </div>
//           </div>

//           {/* BUTTON */}
//           <button
//             onClick={handleSignIn}
//             className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-6"
//           >
//             Sign in
//           </button>

//           <p className="text-center text-sm text-slate-500">
//             Don't have an account?{" "}
//             <button
//               onClick={onNavigateToSignup}
//               className="text-blue-600 hover:underline font-medium"
//             >
//               Sign up
//             </button>
//           </p>
//         </div>
//       </div>
//     </div>
//   );
// }

// // ==================== SIGNUP.JSX ====================
// function Signup({ onNavigateToLogin }) {
//   const [showPassword, setShowPassword] = useState(false);
//   const [showConfirmPassword, setShowConfirmPassword] = useState(false);
//   const [fullName, setFullName] = useState("");
//   const [email, setEmail] = useState("");
//   const [countryCode, setCountryCode] = useState("+1");
//   const [phone, setPhone] = useState("");
//   const [password, setPassword] = useState("");
//   const [confirmPassword, setConfirmPassword] = useState("");
//   const [showOtpModal, setShowOtpModal] = useState(false);
//   const [otp, setOtp] = useState(["", "", "", "", "", ""]);
//   const [generatedOtp, setGeneratedOtp] = useState("");
//   const [isPhoneVerified, setIsPhoneVerified] = useState(false);

//   const sendOtp = () => {
//     if (!phone || phone.length < 6) {
//       alert("Please enter a valid phone number");
//       return;
//     }
//     const newOtp = Math.floor(100000 + Math.random() * 900000).toString();
//     setGeneratedOtp(newOtp);
//     setShowOtpModal(true);
//     alert(`Your OTP is: ${newOtp} (Demo mode - in production, this would be sent via SMS)`);
//   };

//   const handleOtpChange = (index, value) => {
//     if (value.length > 1) value = value.slice(0, 1);
//     if (!/^\d*$/.test(value)) return;

//     const newOtp = [...otp];
//     newOtp[index] = value;
//     setOtp(newOtp);

//     if (value && index < 5) {
//       document.getElementById(`otp-${index + 1}`)?.focus();
//     }
//   };

//   const handleOtpKeyDown = (index, e) => {
//     if (e.key === "Backspace" && !otp[index] && index > 0) {
//       document.getElementById(`otp-${index - 1}`)?.focus();
//     }
//   };

//   const verifyOtp = () => {
//     const enteredOtp = otp.join("");
//     if (enteredOtp === generatedOtp) {
//       setIsPhoneVerified(true);
//       setShowOtpModal(false);
//       alert("Phone number verified successfully!");
//     } else {
//       alert("Invalid OTP. Please try again.");
//     }
//   };

//   const handleCreateAccount = () => {
//     if (!fullName || !email || !phone || !password || !confirmPassword) {
//       alert("Please fill in all fields");
//       return;
//     }
//     if (!isPhoneVerified) {
//       alert("Please verify your phone number first");
//       return;
//     }
//     if (password.length < 6) {
//       alert("Password must be at least 6 characters");
//       return;
//     }
//     if (password !== confirmPassword) {
//       alert("Passwords do not match");
//       return;
//     }
//     alert("Account created successfully! (Demo mode)");
//     onNavigateToLogin();
//   };

//   return (
//     <div className="min-h-screen flex">
//       {/* LEFT PANEL */}
//       <div className="relative hidden lg:flex w-1/2 flex-col bg-gradient-to-br from-[#0B1D36] to-[#020617] px-12 py-10 text-white">
//         {/* TOP CONTENT */}
//         <div>
//           {/* LOGO */}
//           <div className="flex items-center gap-3 mb-20">
//             <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
//               <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
//               </svg>
//             </div>
//             <div>
//               <p className="font-semibold text-lg">Tender Intelligence</p>
//               <p className="text-sm text-slate-400">
//                 Automated Monitoring System
//               </p>
//             </div>
//           </div>

//           {/* HERO TEXT */}
//           <h1 className="text-[42px] font-bold leading-tight mb-6">
//             Start tracking <br />
//             <span className="text-blue-400">opportunities</span> <br />
//             today.
//           </h1>

//           <p className="text-lg text-slate-400 max-w-md mb-14">
//             Join thousands of professionals who never miss a tender opportunity with our automated monitoring system.
//           </p>

//           {/* FEATURES */}
//           <div className="space-y-4">
//             <FeatureItem text="Monitor 62+ government websites" />
//             <FeatureItem text="Real-time keyword alerts" />
//             <FeatureItem text="Power BI analytics integration" />
//             <FeatureItem text="Custom notification settings" />
//           </div>
//         </div>

//         {/* FOOTER FIXED TO BOTTOM */}
//         <p className="absolute bottom-8 text-sm text-slate-400">
//           © 2026 Tender Intelligence System. All rights reserved.
//         </p>
//       </div>

//       {/* RIGHT PANEL */}
//       <div className="flex w-full lg:w-1/2 items-center justify-center px-6 py-8">
//         <div className="w-full max-w-md">
//           <div className="text-center mb-6">
//             <h2 className="text-2xl font-semibold text-slate-900 mb-1">
//               Create an account
//             </h2>
//             <p className="text-sm text-slate-500">
//               Get started with your free account
//             </p>
//           </div>

//           {/* FULL NAME */}
//           <div className="mb-4">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Full name
//             </label>
//             <input
//               type="text"
//               placeholder="John Doe"
//               value={fullName}
//               onChange={(e) => setFullName(e.target.value)}
//               className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//             />
//           </div>

//           {/* EMAIL */}
//           <div className="mb-4">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Email address
//             </label>
//             <input
//               type="email"
//               placeholder="you@company.com"
//               value={email}
//               onChange={(e) => setEmail(e.target.value)}
//               className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//             />
//           </div>

//           {/* PHONE NUMBER */}
//           <div className="mb-4">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Phone number
//             </label>
//             <div className="flex gap-2">
//               <select
//                 value={countryCode}
//                 onChange={(e) => setCountryCode(e.target.value)}
//                 className="rounded-lg border border-slate-200 px-3 py-3 text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
//               >
//                 <option value="+1">🇺🇸 +1</option>
//                 <option value="+93">🇦🇫 +93</option>
//                 <option value="+355">🇦🇱 +355</option>
//                 <option value="+213">🇩🇿 +213</option>
//                 <option value="+376">🇦🇩 +376</option>
//                 <option value="+244">🇦🇴 +244</option>
//                 <option value="+54">🇦🇷 +54</option>
//                 <option value="+374">🇦🇲 +374</option>
//                 <option value="+61">🇦🇺 +61</option>
//                 <option value="+43">🇦🇹 +43</option>
//                 <option value="+994">🇦🇿 +994</option>
//                 <option value="+973">🇧🇭 +973</option>
//                 <option value="+880">🇧🇩 +880</option>
//                 <option value="+375">🇧🇾 +375</option>
//                 <option value="+32">🇧🇪 +32</option>
//                 <option value="+501">🇧🇿 +501</option>
//                 <option value="+229">🇧🇯 +229</option>
//                 <option value="+975">🇧🇹 +975</option>
//                 <option value="+591">🇧🇴 +591</option>
//                 <option value="+387">🇧🇦 +387</option>
//                 <option value="+267">🇧🇼 +267</option>
//                 <option value="+55">🇧🇷 +55</option>
//                 <option value="+673">🇧🇳 +673</option>
//                 <option value="+359">🇧🇬 +359</option>
//                 <option value="+226">🇧🇫 +226</option>
//                 <option value="+257">🇧🇮 +257</option>
//                 <option value="+855">🇰🇭 +855</option>
//                 <option value="+237">🇨🇲 +237</option>
//                 <option value="+1">🇨🇦 +1</option>
//                 <option value="+238">🇨🇻 +238</option>
//                 <option value="+236">🇨🇫 +236</option>
//                 <option value="+235">🇹🇩 +235</option>
//                 <option value="+56">🇨🇱 +56</option>
//                 <option value="+86">🇨🇳 +86</option>
//                 <option value="+57">🇨🇴 +57</option>
//                 <option value="+269">🇰🇲 +269</option>
//                 <option value="+242">🇨🇬 +242</option>
//                 <option value="+506">🇨🇷 +506</option>
//                 <option value="+385">🇭🇷 +385</option>
//                 <option value="+53">🇨🇺 +53</option>
//                 <option value="+357">🇨🇾 +357</option>
//                 <option value="+420">🇨🇿 +420</option>
//                 <option value="+45">🇩🇰 +45</option>
//                 <option value="+253">🇩🇯 +253</option>
//                 <option value="+593">🇪🇨 +593</option>
//                 <option value="+20">🇪🇬 +20</option>
//                 <option value="+503">🇸🇻 +503</option>
//                 <option value="+240">🇬🇶 +240</option>
//                 <option value="+291">🇪🇷 +291</option>
//                 <option value="+372">🇪🇪 +372</option>
//                 <option value="+251">🇪🇹 +251</option>
//                 <option value="+679">🇫🇯 +679</option>
//                 <option value="+358">🇫🇮 +358</option>
//                 <option value="+33">🇫🇷 +33</option>
//                 <option value="+241">🇬🇦 +241</option>
//                 <option value="+220">🇬🇲 +220</option>
//                 <option value="+995">🇬🇪 +995</option>
//                 <option value="+49">🇩🇪 +49</option>
//                 <option value="+233">🇬🇭 +233</option>
//                 <option value="+30">🇬🇷 +30</option>
//                 <option value="+502">🇬🇹 +502</option>
//                 <option value="+224">🇬🇳 +224</option>
//                 <option value="+245">🇬🇼 +245</option>
//                 <option value="+592">🇬🇾 +592</option>
//                 <option value="+509">🇭🇹 +509</option>
//                 <option value="+504">🇭🇳 +504</option>
//                 <option value="+852">🇭🇰 +852</option>
//                 <option value="+36">🇭🇺 +36</option>
//                 <option value="+354">🇮🇸 +354</option>
//                 <option value="+91">🇮🇳 +91</option>
//                 <option value="+62">🇮🇩 +62</option>
//                 <option value="+98">🇮🇷 +98</option>
//                 <option value="+964">🇮🇶 +964</option>
//                 <option value="+353">🇮🇪 +353</option>
//                 <option value="+972">🇮🇱 +972</option>
//                 <option value="+39">🇮🇹 +39</option>
//                 <option value="+225">🇨🇮 +225</option>
//                 <option value="+81">🇯🇵 +81</option>
//                 <option value="+962">🇯🇴 +962</option>
//                 <option value="+7">🇰🇿 +7</option>
//                 <option value="+254">🇰🇪 +254</option>
//                 <option value="+965">🇰🇼 +965</option>
//                 <option value="+996">🇰🇬 +996</option>
//                 <option value="+856">🇱🇦 +856</option>
//                 <option value="+371">🇱🇻 +371</option>
//                 <option value="+961">🇱🇧 +961</option>
//                 <option value="+266">🇱🇸 +266</option>
//                 <option value="+231">🇱🇷 +231</option>
//                 <option value="+218">🇱🇾 +218</option>
//                 <option value="+423">🇱🇮 +423</option>
//                 <option value="+370">🇱🇹 +370</option>
//                 <option value="+352">🇱🇺 +352</option>
//                 <option value="+853">🇲🇴 +853</option>
//                 <option value="+389">🇲🇰 +389</option>
//                 <option value="+261">🇲🇬 +261</option>
//                 <option value="+265">🇲🇼 +265</option>
//                 <option value="+60">🇲🇾 +60</option>
//                 <option value="+960">🇲🇻 +960</option>
//                 <option value="+223">🇲🇱 +223</option>
//                 <option value="+356">🇲🇹 +356</option>
//                 <option value="+222">🇲🇷 +222</option>
//                 <option value="+230">🇲🇺 +230</option>
//                 <option value="+52">🇲🇽 +52</option>
//                 <option value="+373">🇲🇩 +373</option>
//                 <option value="+377">🇲🇨 +377</option>
//                 <option value="+976">🇲🇳 +976</option>
//                 <option value="+382">🇲🇪 +382</option>
//                 <option value="+212">🇲🇦 +212</option>
//                 <option value="+258">🇲🇿 +258</option>
//                 <option value="+95">🇲🇲 +95</option>
//                 <option value="+264">🇳🇦 +264</option>
//                 <option value="+977">🇳🇵 +977</option>
//                 <option value="+31">🇳🇱 +31</option>
//                 <option value="+64">🇳🇿 +64</option>
//                 <option value="+505">🇳🇮 +505</option>
//                 <option value="+227">🇳🇪 +227</option>
//                 <option value="+234">🇳🇬 +234</option>
//                 <option value="+850">🇰🇵 +850</option>
//                 <option value="+47">🇳🇴 +47</option>
//                 <option value="+968">🇴🇲 +968</option>
//                 <option value="+92">🇵🇰 +92</option>
//                 <option value="+970">🇵🇸 +970</option>
//                 <option value="+507">🇵🇦 +507</option>
//                 <option value="+675">🇵🇬 +675</option>
//                 <option value="+595">🇵🇾 +595</option>
//                 <option value="+51">🇵🇪 +51</option>
//                 <option value="+63">🇵🇭 +63</option>
//                 <option value="+48">🇵🇱 +48</option>
//                 <option value="+351">🇵🇹 +351</option>
//                 <option value="+974">🇶🇦 +974</option>
//                 <option value="+40">🇷🇴 +40</option>
//                 <option value="+7">🇷🇺 +7</option>
//                 <option value="+250">🇷🇼 +250</option>
//                 <option value="+966">🇸🇦 +966</option>
//                 <option value="+221">🇸🇳 +221</option>
//                 <option value="+381">🇷🇸 +381</option>
//                 <option value="+248">🇸🇨 +248</option>
//                 <option value="+232">🇸🇱 +232</option>
//                 <option value="+65">🇸🇬 +65</option>
//                 <option value="+421">🇸🇰 +421</option>
//                 <option value="+386">🇸🇮 +386</option>
//                 <option value="+677">🇸🇧 +677</option>
//                 <option value="+252">🇸🇴 +252</option>
//                 <option value="+27">🇿🇦 +27</option>
//                 <option value="+82">🇰🇷 +82</option>
//                 <option value="+211">🇸🇸 +211</option>
//                 <option value="+34">🇪🇸 +34</option>
//                 <option value="+94">🇱🇰 +94</option>
//                 <option value="+249">🇸🇩 +249</option>
//                 <option value="+597">🇸🇷 +597</option>
//                 <option value="+268">🇸🇿 +268</option>
//                 <option value="+46">🇸🇪 +46</option>
//                 <option value="+41">🇨🇭 +41</option>
//                 <option value="+963">🇸🇾 +963</option>
//                 <option value="+886">🇹🇼 +886</option>
//                 <option value="+992">🇹🇯 +992</option>
//                 <option value="+255">🇹🇿 +255</option>
//                 <option value="+66">🇹🇭 +66</option>
//                 <option value="+670">🇹🇱 +670</option>
//                 <option value="+228">🇹🇬 +228</option>
//                 <option value="+676">🇹🇴 +676</option>
//                 <option value="+216">🇹🇳 +216</option>
//                 <option value="+90">🇹🇷 +90</option>
//                 <option value="+993">🇹🇲 +993</option>
//                 <option value="+256">🇺🇬 +256</option>
//                 <option value="+380">🇺🇦 +380</option>
//                 <option value="+971">🇦🇪 +971</option>
//                 <option value="+44">🇬🇧 +44</option>
//                 <option value="+598">🇺🇾 +598</option>
//                 <option value="+998">🇺🇿 +998</option>
//                 <option value="+678">🇻🇺 +678</option>
//                 <option value="+58">🇻🇪 +58</option>
//                 <option value="+84">🇻🇳 +84</option>
//                 <option value="+967">🇾🇪 +967</option>
//                 <option value="+260">🇿🇲 +260</option>
//                 <option value="+263">🇿🇼 +263</option>
//               </select>
//               <input
//                 type="tel"
//                 placeholder="555-000-0000"
//                 value={phone}
//                 onChange={(e) => setPhone(e.target.value)}
//                 disabled={isPhoneVerified}
//                 className={`flex-1 rounded-lg border px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
//                   isPhoneVerified ? 'bg-slate-50 border-green-300' : 'border-slate-200'
//                 }`}
//               />
//               {!isPhoneVerified ? (
//                 <button
//                   type="button"
//                   onClick={sendOtp}
//                   className="px-5 py-3 rounded-lg bg-blue-500 text-white font-medium hover:bg-blue-600 transition whitespace-nowrap"
//                 >
//                   Verify
//                 </button>
//               ) : (
//                 <div className="flex items-center px-4 py-3 rounded-lg bg-green-50 border border-green-300">
//                   <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//                   </svg>
//                 </div>
//               )}
//             </div>
//             {isPhoneVerified && (
//               <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
//                 <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//                 </svg>
//                 Phone number verified
//               </p>
//             )}
//           </div>

//           {/* PASSWORD */}
//           <div className="mb-4">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Password
//             </label>
//             <div className="relative">
//               <input
//                 type={showPassword ? "text" : "password"}
//                 placeholder="••••••••"
//                 value={password}
//                 onChange={(e) => setPassword(e.target.value)}
//                 className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//               />
//               <button
//                 type="button"
//                 onClick={() => setShowPassword(!showPassword)}
//                 className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//               >
//                 {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//               </button>
//             </div>
//             <p className="text-xs text-slate-500 mt-1">Must be at least 6 characters</p>
//           </div>

//           {/* CONFIRM PASSWORD */}
//           <div className="mb-5">
//             <label className="block text-sm font-medium text-slate-700 mb-2">
//               Confirm password
//             </label>
//             <div className="relative">
//               <input
//                 type={showConfirmPassword ? "text" : "password"}
//                 placeholder="••••••••"
//                 value={confirmPassword}
//                 onChange={(e) => setConfirmPassword(e.target.value)}
//                 className="w-full rounded-lg border border-slate-200 px-4 py-3 text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
//               />
//               <button
//                 type="button"
//                 onClick={() => setShowConfirmPassword(!showConfirmPassword)}
//                 className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400"
//               >
//                 {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
//               </button>
//             </div>
//           </div>

//           {/* BUTTON */}
//           <button
//             onClick={handleCreateAccount}
//             className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-5"
//           >
//             Create account
//           </button>

//           <p className="text-center text-sm text-slate-500">
//             Already have an account?{" "}
//             <button
//               onClick={onNavigateToLogin}
//               className="text-blue-600 hover:underline font-medium"
//             >
//               Sign in
//             </button>
//           </p>
//         </div>
//       </div>

//       {/* OTP MODAL */}
//       {showOtpModal && (
//         <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
//           <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
//             <div className="text-center mb-6">
//               <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
//                 <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                   <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
//                 </svg>
//               </div>
//               <h3 className="text-2xl font-semibold text-slate-900 mb-2">
//                 Verify Your Phone
//               </h3>
//               <p className="text-slate-500 text-sm">
//                 Enter the 6-digit code sent to<br />
//                 <span className="font-medium text-slate-700">{countryCode} {phone}</span>
//               </p>
//             </div>

//             <div className="flex gap-2 justify-center mb-6">
//               {otp.map((digit, index) => (
//                 <input
//                   key={index}
//                   id={`otp-${index}`}
//                   type="text"
//                   maxLength={1}
//                   value={digit}
//                   onChange={(e) => handleOtpChange(index, e.target.value)}
//                   onKeyDown={(e) => handleOtpKeyDown(index, e)}
//                   className="w-12 h-14 text-center text-xl font-semibold rounded-lg border-2 border-slate-200 focus:border-blue-500 focus:outline-none text-slate-700"
//                 />
//               ))}
//             </div>

//             <button
//               onClick={verifyOtp}
//               className="w-full rounded-lg bg-blue-500 py-3 font-medium text-white hover:bg-blue-600 transition mb-3"
//             >
//               Verify OTP
//             </button>

//             <button
//               onClick={() => setShowOtpModal(false)}
//               className="w-full rounded-lg border border-slate-200 py-3 font-medium text-slate-700 hover:bg-slate-50 transition"
//             >
//               Cancel
//             </button>

//             <div className="text-center mt-4">
//               <button
//                 onClick={sendOtp}
//                 className="text-sm text-blue-600 hover:underline"
//               >
//                 Resend OTP
//               </button>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// // ==================== SHARED COMPONENTS ====================
// function StatCard({ title, subtitle }) {
//   return (
//     <div className="rounded-xl bg-white/5 px-6 py-5 border border-white/5">
//       <p className="text-xl font-semibold">{title}</p>
//       <p className="text-sm text-slate-400">{subtitle}</p>
//     </div>
//   );
// }

// function FeatureItem({ text }) {
//   return (
//     <div className="flex items-center gap-3">
//       <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center">
//         <svg className="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
//         </svg>
//       </div>
//       <p className="text-slate-300">{text}</p>
//     </div>
//   );
// }
