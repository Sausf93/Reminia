/** Pantalla de acceso. Guarda el JWT + centro_id/rol vía AuthContext. */
import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Field, inputStyle } from "../components/ui";
import { Logo } from "../components/Logo";
import { colors, radius, shadow } from "../theme";

const DEMO_EMAIL = "admin@trazo.local";
const DEMO_PASS = "trazo1234";

export function LoginPage() {
  const { session, signIn } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // Tras pagar el alta, Stripe redirige a "/?alta=ok": el acceso llega por correo.
  const pagoConfirmado = params.get("alta") === "ok";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [verPass, setVerPass] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Si ya hay sesión, no tiene sentido mostrar el login.
  if (session) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signIn(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo iniciar sesión. Inténtalo de nuevo.",
      );
    } finally {
      setLoading(false);
    }
  }

  function rellenarDemo() {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASS);
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        background: colors.ivory,
      }}
    >
      <div style={{ width: "100%", maxWidth: 420 }}>
        <div style={{ textAlign: "center", marginBottom: 24, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <Logo size={48} textSize={40} />
          <p className="eyebrow" style={{ marginTop: 10 }}>Panel del centro</p>
        </div>

        <form
          onSubmit={onSubmit}
          style={{
            background: colors.white,
            border: `1px solid ${colors.sand}`,
            borderRadius: radius.lg,
            padding: "30px 28px",
            boxShadow: shadow.soft,
          }}
        >
          <h1 style={{ fontSize: 24, marginBottom: 4 }}>Acceso al panel</h1>
          <p style={{ color: colors.textMuted, fontSize: 14.5, marginBottom: 22 }}>
            Introduce las credenciales del centro para ver la evolución de las personas usuarias.
          </p>

          {pagoConfirmado && (
            <div
              role="status"
              style={{
                background: colors.card,
                border: `1px solid ${colors.sage}`,
                color: colors.ink,
                borderRadius: radius.sm,
                padding: "12px 14px",
                fontSize: 14,
                lineHeight: 1.5,
                marginBottom: 18,
              }}
            >
              <strong>¡Pago confirmado!</strong> Te hemos enviado un correo con un
              enlace para crear tu contraseña. Revisa tu bandeja (y el spam) para
              entrar por primera vez.
            </div>
          )}

          <Field label="Correo electrónico" htmlFor="email">
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
              placeholder="nombre@centro.local"
            />
          </Field>

          <Field label="Contraseña" htmlFor="password">
            <div style={{ position: "relative" }}>
              <input
                id="password"
                type={verPass ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ ...inputStyle, paddingRight: 46 }}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setVerPass((v) => !v)}
                aria-label={verPass ? "Ocultar contraseña" : "Mostrar contraseña"}
                aria-pressed={verPass}
                style={{
                  position: "absolute",
                  right: 6,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  padding: 8,
                  display: "grid",
                  placeItems: "center",
                  color: colors.textMuted,
                  cursor: "pointer",
                  borderRadius: radius.sm,
                }}
              >
                {verPass ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7c-2 0-3.8-.6-5.3-1.5" />
                    <circle cx="12" cy="12" r="3" />
                    <path d="M3 3l18 18" />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </Field>

          {error && (
            <div
              role="alert"
              style={{
                background: colors.alertBg,
                border: `1px solid ${colors.coral}`,
                color: colors.coralDark,
                borderRadius: radius.sm,
                padding: "10px 12px",
                fontSize: 14,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          <Button type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Entrando…" : "Entrar"}
          </Button>

          <p style={{ textAlign: "center", marginTop: 16, marginBottom: 0, fontSize: 13.5 }}>
            <Link to="/recuperar" style={{ color: colors.sageDark, fontWeight: 600 }}>
              ¿Olvidaste tu contraseña?
            </Link>
          </p>
        </form>

        {import.meta.env.DEV && (
          <div
            style={{
              marginTop: 16,
              background: colors.card,
              border: `1px dashed ${colors.sand}`,
              borderRadius: radius.md,
              padding: "14px 16px",
              fontSize: 13.5,
              color: colors.textMuted,
            }}
          >
            <strong style={{ color: colors.ink }}>Credenciales de demostración</strong>
            <div className="mono" style={{ marginTop: 6, lineHeight: 1.7 }}>
              {DEMO_EMAIL} / {DEMO_PASS}
            </div>
            <button
              type="button"
              onClick={rellenarDemo}
              style={{
                marginTop: 10,
                background: "transparent",
                border: `1.5px solid ${colors.sage}`,
                color: colors.sageDark,
                borderRadius: radius.sm,
                padding: "7px 14px",
                fontWeight: 600,
                fontSize: 13.5,
              }}
            >
              Usar credenciales demo
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
