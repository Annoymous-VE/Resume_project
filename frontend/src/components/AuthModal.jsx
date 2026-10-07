import React, { useState, useEffect } from "react";
import { loginUser, registerUser } from "../api/client";

export default function AuthModal({ isOpen, onClose, onAuthSuccess, initialMode = "login" }) {
  const [mode, setMode] = useState(initialMode); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setMode(initialMode);
    setError(null);
  }, [initialMode, isOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setError("Please enter your email address.");
      return;
    }

    if (!password) {
      setError("Please enter your password.");
      return;
    }

    if (mode === "signup" && password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setLoading(true);
    try {
      let res;
      if (mode === "login") {
        res = await loginUser({ email: cleanEmail, password });
      } else {
        res = await registerUser({
          email: cleanEmail,
          password,
          full_name: fullName.trim()
        });
      }

      if (res && res.user) {
        onAuthSuccess(res.user);
        onClose();
      }
    } catch (err) {
      setError(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={onClose}>
      <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="auth-modal-header">
          <div className="auth-modal-badge">
            <span className="auth-modal-badge-dot" />
            {mode === "login" ? "Welcome Back" : "Get Started Free"}
          </div>
          <button
            type="button"
            className="auth-modal-close"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="auth-modal-tabs">
          <button
            type="button"
            className={`auth-modal-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-modal-tab ${mode === "signup" ? "active" : ""}`}
            onClick={() => {
              setMode("signup");
              setError(null);
            }}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="auth-modal-error">
            <span style={{ fontSize: "1.1rem" }}>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="auth-modal-form">
          {mode === "signup" && (
            <div className="form-group">
              <label className="form-label" htmlFor="auth-fullname">
                Full Name
              </label>
              <input
                id="auth-fullname"
                type="text"
                className="form-input"
                placeholder="e.g. Alex Chen"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={loading}
                autoFocus
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="auth-email">
              Email Address
            </label>
            <input
              id="auth-email"
              type="email"
              className="form-input"
              placeholder="alex@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              autoFocus={mode === "login"}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="auth-password">
              Password
            </label>
            <div className="auth-password-wrapper">
              <input
                id="auth-password"
                type={showPassword ? "text" : "password"}
                className="form-input auth-password-input"
                placeholder={mode === "signup" ? "Min. 6 characters" : "••••••••"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
              <button
                type="button"
                className="auth-password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "👁️" : "👁️‍🗨️"}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary auth-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="auth-btn-spinner-wrap">
                <span className="auth-spinner" />
                {mode === "login" ? "Signing In..." : "Creating Account..."}
              </span>
            ) : mode === "login" ? (
              "Sign In to Your Account"
            ) : (
              "Create Your Free Account"
            )}
          </button>
        </form>

        {/* Footer switch prompt */}
        <div className="auth-modal-footer">
          {mode === "login" ? (
            <p>
              Don't have an account?{" "}
              <button
                type="button"
                className="auth-switch-link"
                onClick={() => {
                  setMode("signup");
                  setError(null);
                }}
              >
                Create one now →
              </button>
            </p>
          ) : (
            <p>
              Already have an account?{" "}
              <button
                type="button"
                className="auth-switch-link"
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
              >
                Sign in here →
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
