/**
 * Crear/restablecer la contraseña desde el ENLACE del correo (alta self-service
 * o recuperación). El token del enlace es la credencial de un solo uso; al fijar
 * la contraseña el backend devuelve un JWT y entramos directos (auto-login).
 */
import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { crearPassword } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { Button, Field, inputStyle } from "../components/ui";
import { colors, radius, shadow } from "../theme";

const MIN = 8;

export function CrearPasswordPage() {
  const { session, applyToken } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Si ya hay sesión iniciada, no tiene sentido crear la contraseña.
  if (session) return <Navigate to="/" replace />;

  const sinToken = token.trim() === "";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < MIN) {
      setError(`La contraseña debe tener al menos ${MIN} caracteres.`);
      return;
    }
    if (password !== confirm) {
      setError("Las dos contraseñas no coinciden.");
      return;
    }
    setLoading(true);
    try {
      const tk = await crearPassword(token, password);
      applyToken(tk); // auto-login
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo crear la contraseña. Inténtalo de nuevo.",
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
          <h1 style={{ fontSize: 24, marginBottom: 4 }}>Crea tu contraseña</h1>
          <p style={{ color: colors.textMuted, fontSize: 14.5, marginBottom: 22 }}>
            Elige una contraseña para entrar al panel. Con ella accederás a partir
            de ahora.
          </p>

          {sinToken ? (
            <div
              role="alert"
              style={{
                background: colors.alertBg,
                border: `1px solid ${colors.coral}`,
                color: colors.coralDark,
                borderRadius: radius.sm,
                padding: "12px 14px",
                fontSize: 14,
              }}
            >
              El enlace no es válido o está incompleto. Pide uno nuevo desde{" "}
              <Link to="/recuperar" style={{ color: colors.coralDark, fontWeight: 700 }}>
                recuperar acceso
              </Link>
              .
            </div>
          ) : (
            <form onSubmit={onSubmit}>
              <Field
                label="Nueva contraseña"
                htmlFor="password"
                hint={`Al menos ${MIN} caracteres.`}
              >
                <input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={MIN}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={inputStyle}
                  placeholder="••••••••"
                />
              </Field>

              <Field label="Repite la contraseña" htmlFor="confirm">
                <input
                  id="confirm"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={MIN}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  style={inputStyle}
                  placeholder="••••••••"
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
                {loading ? "Guardando…" : "Guardar y entrar"}
              </Button>
            </form>
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
