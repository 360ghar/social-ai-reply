"use client";
import { ReactNode, useEffect } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  danger?: boolean;
}

export function Modal({ open, onClose, title, children, footer, danger }: ModalProps) {
  useEffect(() => {
    if (open) {
      const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose();
      window.addEventListener("keydown", handler);
      document.body.style.overflow = "hidden";
      return () => {
        window.removeEventListener("keydown", handler);
        document.body.style.overflow = "";
      };
    }
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="modal-header">
          <h3 className="modal-title">{title}</h3>
          <button className="modal-close ghost-button" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

interface ConfirmModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  danger?: boolean;
  loading?: boolean;
}

export function ConfirmModal({ open, onClose, onConfirm, title, message, confirmText = "Confirm", danger = false, loading = false }: ConfirmModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <div className="flex gap-md" style={{ justifyContent: "flex-end" }}>
          <button className="secondary-button" onClick={onClose} disabled={loading}>Cancel</button>
          <button className={danger ? "danger-button" : "primary-button"} onClick={onConfirm} disabled={loading}>
            {loading ? <span className="spinner spinner-sm" /> : null}
            {confirmText}
          </button>
        </div>
      }
    >
      <p style={{ color: "var(--muted)", lineHeight: 1.5 }}>{message}</p>
    </Modal>
  );
}
