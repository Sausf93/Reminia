/**
 * Recuperar acceso: pide el correo y dispara el envío de un enlace para elegir
 * una contraseña nueva. Por privacidad, la respuesta es SIEMPRE la misma exista
 * o no la cuenta (no revelamos qué correos están registrados).
 */
import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { recuperarAcceso } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { Button, Field, inputStyle } from "../components/ui";
import { colors, radius, shadow } from "../theme";

export function RecuperarPage() {
  const { session } = useAuth();
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (session) return <Navigate to="/" replace />;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await recuperarAcceso(email.trim());
      setEnviado(true);
    } catch (err) {
      // Un 429 (demasiados intentos) u otro error sí se muestra; el 200 normal
      // no revela existencia (el mensaje es el mismo pase lo que pase).
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo enviar el enlace. Inténtalo de nuevo.",
      );
    } finally {
      setLoading(false);
    }
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
        <div
          style={{
            textAlign: "center",
            marginBottom: 24,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <Logo size={48} textSize={40} />
          <p className="eyebrow" style={{ marginTop: 10 }}>
            Panel del centro
          </p>
        </div>

        <div
          style={{
            background: colors.white,
            border: `1px solid ${colors.sand}`,
            borderRadius: radius.lg,
            padding: "30px 28px",
            boxShadow: shadow.soft,
          }}
        >
          <h1 style={{ fontSize: 24, marginBottom: 4 }}>Recuperar acceso</h1>

          {enviado ? (
            <div
              role="status"
              style={{
                background: colors.card,
                border: `1px solid ${colors.sage}`,
                color: colors.ink,
                borderRadius: radius.sm,
                padding: "14px 16px",
                fontSize: 14.5,
                lineHeight: 1.5,
                marginTop: 10,
              }}
            >
              Si ese correo tiene una cuenta, te hemos enviado un enlace para
              elegir una contraseña nueva. Revisa tu bandeja (y la carpeta de
              spam). El enlace caduca en 1 hora.
            </div>
          ) : (
            <>
              <p style={{ color: colors.textMuted, fontSize: 14.5, marginBottom: 22 }}>
                Escribe tu correo y te enviaremos un enlace para elegir una
                contraseña nueva.
              </p>
              <form onSubmit={onSubmit}>
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
                  {loading ? "Enviando…" : "Enviarme el enlace"}
                </Button>
              </form>
            </>
          )}
        </div>

        <p style={{ textAlign: "center", marginTop: 16, fontSize: 13.5 }}>
          <Link to="/login" style={{ color: colors.sageDark, fontWeight: 600 }}>
            Volver al acceso
          </Link>
        </p>
      </div>
    </div>
  );
}
