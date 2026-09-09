/**
 * Diálogo de confirmación in-app (sustituye a window.confirm / window.prompt,
 * que rompían la estética del panel). Dos modos:
 *  - normal: Aceptar / Cancelar.
 *  - peligro + requireText: acción irreversible (p. ej. supresión RGPD); exige
 *    teclear un texto EXACTO (el alias) antes de habilitar el botón. Ese seguro
 *    NO se relaja: es la garantía contra un borrado accidental.
 */
import { useEffect, useRef, useState } from "react";
import { colors, radius, shadow } from "../theme";
import { Button } from "./ui";

export function ConfirmDialog({
  open,
  title,
  mensaje,
  confirmLabel = "Aceptar",
  tone = "normal",
  requireText,
  loading = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  mensaje: React.ReactNode;
  confirmLabel?: string;
  tone?: "normal" | "peligro";
  /** Si se pasa, hay que teclearlo EXACTO para habilitar el botón (irreversible). */
  requireText?: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [texto, setTexto] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setTexto("");
      // Al abrir, lleva el foco al diálogo: al campo si hay que teclear (RGPD),
      // o a la propia tarjeta si no (así Escape/Tab quedan dentro y el lector de
      // pantalla lo anuncia). Deja que el elemento se monte antes de enfocar.
      const t = setTimeout(() => (inputRef.current ?? cardRef.current)?.focus(), 40);
      return () => clearTimeout(t);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  const necesitaTexto = !!requireText;
  const coincide = !necesitaTexto || texto.trim() === requireText;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onCancel();
      }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 900,
        background: "rgba(18, 49, 46, 0.5)",
        backdropFilter: "blur(2px)",
        display: "grid",
        placeItems: "center",
        padding: 20,
      }}
    >
      <div
        ref={cardRef}
        tabIndex={-1}
        style={{
          width: "100%",
          maxWidth: 440,
          outline: "none",
          background: colors.white,
          border: `1px solid ${colors.sand}`,
          borderRadius: radius.lg,
          padding: "26px 26px 22px",
          boxShadow: shadow.soft,
        }}
      >
        <h2 style={{ fontSize: 20, marginBottom: 8, color: colors.ink }}>{title}</h2>
        <div style={{ color: colors.textMuted, fontSize: 14.5, lineHeight: 1.55 }}>{mensaje}</div>

        {necesitaTexto && (
          <div style={{ marginTop: 16 }}>
            <label
              htmlFor="confirm-text"
              style={{ display: "block", fontSize: 13, color: colors.textMuted, marginBottom: 6 }}
            >
              Para confirmar, escribe: <strong style={{ color: colors.ink }}>{requireText}</strong>
            </label>
            <input
              id="confirm-text"
              ref={inputRef}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              autoComplete="off"
              style={{
                width: "100%",
                padding: "11px 13px",
                borderRadius: radius.sm,
                border: `1.5px solid ${coincide ? colors.sageDark : colors.bordeControl}`,
                background: colors.white,
                color: colors.ink,
              }}
            />
          </div>
        )}

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
          <Button variant="ghost" onClick={onCancel} disabled={loading}>
            Cancelar
          </Button>
          <Button
            variant={tone === "peligro" ? "coral" : "primary"}
            onClick={onConfirm}
            disabled={loading || !coincide}
          >
            {loading ? "Un momento…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
