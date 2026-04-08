"use client";

import { useState, InputHTMLAttributes } from "react";

interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  showStrength?: boolean;
  error?: string;
}

function getStrength(password: string): { level: "weak" | "fair" | "strong"; percent: number } {
  if (!password) return { level: "weak", percent: 0 };
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  if (score <= 2) return { level: "weak", percent: 33 };
  if (score <= 3) return { level: "fair", percent: 66 };
  return { level: "strong", percent: 100 };
}

export function PasswordInput({ showStrength, error, className, ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const value = typeof props.value === "string" ? props.value : "";
  const strength = showStrength ? getStrength(value) : null;

  return (
    <div className="password-input-wrapper">
      <div style={{ position: "relative" }}>
        <input
          {...props}
          type={visible ? "text" : "password"}
          className={className}
          style={{ ...props.style, paddingRight: 40 }}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible(!visible)}
          tabIndex={-1}
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
              <line x1="1" y1="1" x2="23" y2="23"/>
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          )}
        </button>
      </div>
      {strength && value && (
        <div className="password-strength">
          <div className="password-strength-bar">
            <div
              className={`password-strength-fill password-strength-${strength.level}`}
              style={{ width: `${strength.percent}%` }}
            />
          </div>
          <span className={`password-strength-label password-strength-${strength.level}`}>
            {strength.level === "weak" ? "Weak" : strength.level === "fair" ? "Fair" : "Strong"}
          </span>
        </div>
      )}
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}
