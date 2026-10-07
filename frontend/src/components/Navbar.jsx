import React from "react";

export default function Navbar({
  currentUser,
  onOpenAuth,
  onLogout,
  onResetToHome,
  viewMode = "wizard",
  onViewChange
}) {
  const getInitials = (user) => {
    if (!user) return "?";
    if (user.full_name && user.full_name.trim()) {
      const parts = user.full_name.trim().split(/\s+/);
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return parts[0].slice(0, 2).toUpperCase();
    }
    if (user.email) {
      return user.email.slice(0, 2).toUpperCase();
    }
    return "U";
  };

  return (
    <header className="app-navbar">
      <div className="app-navbar-inner">
        {/* Brand */}
        <div className="app-navbar-brand" onClick={onResetToHome} role="button" tabIndex={0}>
          <div className="brand-logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <span className="brand-title">
            Resume<span className="brand-highlight">Case</span>
          </span>
          <span className="brand-badge">AI Interviewer</span>
        </div>

        {/* Center Navigation Links (Visible only when logged in) */}
        {currentUser && (
          <nav className="navbar-nav-links">
            <button
              type="button"
              className={`navbar-nav-item ${viewMode === "wizard" ? "active" : ""}`}
              onClick={() => onViewChange && onViewChange("wizard")}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
              <span>Interview Wizard</span>
            </button>

            <button
              type="button"
              className={`navbar-nav-item ${viewMode === "dashboard" ? "active" : ""}`}
              onClick={() => onViewChange && onViewChange("dashboard")}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
              </svg>
              <span>Dashboard</span>
            </button>
          </nav>
        )}

        {/* Right Actions */}
        <div className="app-navbar-actions">
          {currentUser ? (
            <div className="user-profile-menu">
              <div className="user-profile-pill">
                <div className="user-avatar-circle">
                  {getInitials(currentUser)}
                </div>
                <div className="user-profile-info">
                  <span className="user-profile-name">
                    {currentUser.full_name || currentUser.email.split("@")[0]}
                  </span>
                  <span className="user-profile-email">{currentUser.email}</span>
                </div>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-sm navbar-logout-btn"
                onClick={onLogout}
                title="Sign out of your account"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <div className="navbar-guest-actions">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => onOpenAuth("login")}
              >
                Sign In
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onOpenAuth("signup")}
              >
                Create Account
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
