// LoginForm.jsx
import React, { useState } from 'react';
import './LoginForm.css';

function CapsuleMark({ size = 44 }) {
  // The app's logo: a capsule, half white and half amber, tilted.
  return (
    <svg
      className="lg-capsule-mark"
      width={size}
      height={size}
      viewBox="0 0 48 48"
      aria-hidden="true"
    >
      <g transform="rotate(-40 24 24)">
        <path d="M24 12h-9a12 12 0 0 0 0 24h9z" fill="#ffffff" />
        <path d="M24 12h9a12 12 0 0 1 0 24h-9z" fill="#E8A33D" />
        <rect x="23" y="12" width="2" height="24" fill="#0B3D2E" opacity="0.18" />
      </g>
    </svg>
  );
}

function FeatureIcon({ children }) {
  return (
    <span className="lg-feature-icon" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {children}
      </svg>
    </span>
  );
}

export default function LoginForm({ onSubmit, isLoading, error }) {
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="lg-page">
      {/* Brand panel */}
      <aside className="lg-brand">
        <div className="lg-brand-top">
          <CapsuleMark />
          <span className="lg-brand-name">Pharmacy Inventory</span>
        </div>

        <div className="lg-brand-body">
          <h1 className="lg-headline">
            Know what is on the shelf, and what is about to expire.
          </h1>

          <ul className="lg-features">
            <li>
              <FeatureIcon>
                <path d="M3 7l9-4 9 4-9 4-9-4z" />
                <path d="M3 12l9 4 9-4" />
                <path d="M3 17l9 4 9-4" />
              </FeatureIcon>
              <span>
                <strong>Stock levels</strong>
                See low stock before it runs out.
              </span>
            </li>
            <li>
              <FeatureIcon>
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </FeatureIcon>
              <span>
                <strong>Expiry alerts</strong>
                Spot medicines that are close to their expiry date.
              </span>
            </li>
            <li>
              <FeatureIcon>
                <path d="M9 11l3 3 8-8" />
                <path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h9" />
              </FeatureIcon>
              <span>
                <strong>Every change recorded</strong>
                Who changed what, and when.
              </span>
            </li>
          </ul>
        </div>

        {/* Decorative capsules */}
        <svg className="lg-pattern" viewBox="0 0 400 400" aria-hidden="true">
          <g fill="none" stroke="#ffffff" strokeWidth="2" opacity="0.14">
            <rect x="220" y="40" width="150" height="64" rx="32" transform="rotate(-35 295 72)" />
            <rect x="120" y="190" width="190" height="80" rx="40" transform="rotate(-35 215 230)" />
            <rect x="260" y="290" width="120" height="52" rx="26" transform="rotate(-35 320 316)" />
          </g>
        </svg>
      </aside>

      {/* Form panel */}
      <main className="lg-main">
        <div className="lg-mobile-brand">
          <CapsuleMark size={34} />
          <span>Pharmacy Inventory</span>
        </div>

        <div className="lg-form-wrap">
          <h2 className="lg-title">Sign in</h2>
          <p className="lg-subtitle">
            Use the account your pharmacy manager set up for you.
          </p>

          <form onSubmit={handleSubmit} noValidate={false}>
            {error && (
              <div className="lg-alert" role="alert">
                {error}
              </div>
            )}

            <div className="lg-field">
              <label htmlFor="lg-username">Username</label>
              <input
                id="lg-username"
                type="text"
                name="username"
                autoComplete="username"
                autoFocus
                required
                value={formData.username}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>

            <div className="lg-field">
              <label htmlFor="lg-password">Password</label>
              <div className="lg-password">
                <input
                  id="lg-password"
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  autoComplete="current-password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="lg-toggle"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                  disabled={isLoading}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            <button type="submit" className="lg-submit" disabled={isLoading}>
              {isLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="lg-help">
            Forgot your password? Ask your pharmacy manager to reset it.
          </p>
        </div>
      </main>
    </div>
  );
}