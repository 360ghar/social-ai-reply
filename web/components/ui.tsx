"use client";
import { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes, forwardRef } from "react";
export { Modal, ConfirmModal } from "./modal";

// ── Loading Spinner ──────────────────────────────────────────────
export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  return <span className={`spinner spinner-${size}`} style={{ borderTopColor: "var(--accent)" }} />;
}

// ── Button with loading state ────────────────────────────────────
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  loading?: boolean;
  children: ReactNode;
}

export function Button({ variant = "primary", loading, children, disabled, className, ...props }: ButtonProps) {
  const cls = `${variant}-button ${loading ? "is-loading" : ""} ${className || ""}`.trim();
  return (
    <button className={cls} disabled={disabled || loading} {...props}>
      {loading && <Spinner size="sm" />}
      <span style={loading ? { opacity: 0.7 } : undefined}>{children}</span>
    </button>
  );
}

// ── Empty State ──────────────────────────────────────────────────
interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon = "📭", title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      {description && <p className="empty-state-description">{description}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}

// ── Skeleton Loader ──────────────────────────────────────────────
export function Skeleton({ width, height = 20, rounded = false }: { width?: number | string; height?: number; rounded?: boolean }) {
  return (
    <div
      className={`skeleton ${rounded ? "skeleton-circle" : "skeleton-text"}`}
      style={{ width: width || "100%", height, borderRadius: rounded ? "50%" : "var(--radius-sm)" }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ padding: "var(--space-xl)" }}>
      <Skeleton height={16} width="40%" />
      <div style={{ marginTop: 12 }}><Skeleton height={12} width="80%" /></div>
      <div style={{ marginTop: 8 }}><Skeleton height={12} width="60%" /></div>
    </div>
  );
}

// ── KPI Card ─────────────────────────────────────────────────────
interface KpiCardProps {
  label: string;
  value: string | number;
  trend?: { value: number; label: string };
  onClick?: () => void;
}

export function KpiCard({ label, value, trend, onClick }: KpiCardProps) {
  return (
    <div className="kpi-card card" onClick={onClick} style={onClick ? { cursor: "pointer" } : undefined}>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      {trend && (
        <div className={`kpi-trend ${trend.value >= 0 ? "kpi-trend-up" : "kpi-trend-down"}`}>
          {trend.value >= 0 ? "↑" : "↓"} {Math.abs(trend.value)}% {trend.label}
        </div>
      )}
    </div>
  );
}

// ── Progress Bar / Usage Meter ───────────────────────────────────
interface UsageMeterProps {
  label: string;
  used: number;
  limit: number;
}

export function UsageMeter({ label, used, limit }: UsageMeterProps) {
  const isUnlimited = limit >= 999999;
  const pct = isUnlimited ? 100 : limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  const isWarning = !isUnlimited && pct >= 80;
  const isOver = !isUnlimited && pct >= 100;
  return (
    <div className="usage-meter">
      <div className="flex justify-between" style={{ marginBottom: 4 }}>
        <span className="field-label">{label}</span>
        <span className={`text-sm ${isOver ? "text-error" : isWarning ? "text-warning" : "text-muted"}`}>
          {isUnlimited ? `${used} active | Unlocked` : `${used} / ${limit}`}
        </span>
      </div>
      <div className="progress-bar">
        <div
          className="progress-bar-fill"
          style={{
            width: `${pct}%`,
            backgroundColor: isUnlimited
              ? "var(--accent)"
              : isOver
                ? "var(--error)"
                : isWarning
                  ? "var(--warning)"
                  : "var(--accent)",
          }}
        />
      </div>
    </div>
  );
}

// ── Step Indicator ───────────────────────────────────────────────
interface StepIndicatorProps {
  steps: { label: string; done: boolean }[];
  currentStep: number;
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="step-indicator">
      {steps.map((s, i) => (
        <div key={i} style={{ display: "contents" }}>
          <div className={`step ${s.done ? "done" : i === currentStep ? "active" : ""}`}>
            {s.done ? "✓" : i + 1}
          </div>
          {i < steps.length - 1 && <div className={`step-line ${s.done ? "done" : ""}`} />}
        </div>
      ))}
    </div>
  );
}

// ── Tabs ─────────────────────────────────────────────────────────
interface TabsProps {
  tabs: { key: string; label: string; count?: number }[];
  active: string;
  onChange: (key: string) => void;
}

export function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <button
          key={t.key}
          className={`tab ${active === t.key ? "active" : ""}`}
          onClick={() => onChange(t.key)}
        >
          {t.label}
          {t.count !== undefined && !isNaN(t.count) && <span className="badge" style={{ marginLeft: 6 }}>{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

// ── Score Badge ──────────────────────────────────────────────────
export function ScoreBadge({ score }: { score: number }) {
  const cls = score >= 70 ? "badge-success" : score >= 40 ? "badge-warning" : "badge-error";
  return <span className={`score-pill ${cls}`}>{score}</span>;
}

// ── Badge ────────────────────────────────────────────────────────────
interface BadgeProps {
  variant?: "default" | "success" | "warning" | "error" | "info";
  children: ReactNode;
}

export function Badge({ variant = "default", children }: BadgeProps) {
  const cls = `badge badge-${variant}`;
  return <span className={cls}>{children}</span>;
}

// ── Tooltip ──────────────────────────────────────────────────────────
interface TooltipProps {
  text: string;
  children: ReactNode;
}

export function Tooltip({ text, children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  return (
    <div
      style={{ position: "relative", display: "inline-block" }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && <div className="tooltip visible">{text}</div>}
    </div>
  );
}

// ── Platform Icon ────────────────────────────────────────────────
export function PlatformIcon({ platform }: { platform: string }) {
  const icons: Record<string, string> = { reddit: "🟠", quora: "🔴", facebook: "🔵", default: "🌐" };
  return <span className="platform-icon" title={platform}>{icons[platform] || icons.default}</span>;
}

// ── Drawer ───────────────────────────────────────────────────────
interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Drawer({ open, onClose, title, children, footer }: DrawerProps) {
  if (!open) return null;
  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-header">
          <h3 className="modal-title">{title}</h3>
          <button className="ghost-button modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-footer">{footer}</div>}
      </div>
    </>
  );
}

// ── Notification Bell ────────────────────────────────────────────
interface NotificationBellProps {
  count: number;
  onClick: () => void;
}

export function NotificationBell({ count, onClick }: NotificationBellProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  return (
    <div style={{ position: "relative" }}>
      <button
        className="ghost-button"
        onClick={() => {
          setDropdownOpen(!dropdownOpen);
          onClick();
        }}
        style={{
          position: "relative",
          fontSize: 16,
          padding: "8px 12px",
          height: "36px",
          display: "flex",
          alignItems: "center",
        }}
        title="Notifications"
      >
        🔔
        {count > 0 && <span className="notification-badge">{count > 9 ? "9+" : count}</span>}
      </button>
    </div>
  );
}
