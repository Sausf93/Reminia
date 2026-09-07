/**
 * Paywall global. Cuando el backend corta el acceso por suscripción (prueba
 * caducada, centro suspendido o impago), `client.ts` emite el evento
 * `reminia:acceso-cortado`. Aquí lo escuchamos y mostramos UNA pantalla clara
 * "el acceso está en pausa → Activar suscripción (pagar)", en vez de dejar
 * errores sueltos por cada página. El camino de pago sigue abierto aunque la
 * prueba haya caducado (el backend lo garantiza), así que el admin puede pagar
 * desde aquí sin salir.
 */
import { useEffect, useState } from "react";
import { crearCheckoutSuscripcion } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { colors, radius, shadow } from "../theme";
import { Logo } from "./Logo";
import { Button } from "./ui";

export function PaywallOverlay() {
  const { isAdmin, signOut } = useAuth();
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [pagando, setPagando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onCorte(e: Event) {
      const detalle = (e as CustomEvent).detail as { mensaje?: string } | undefined;
      setMensaje(
        detalle?.mensaje ||
          "El acceso del centro está en pausa. Activa la suscripción para seguir usando Reminia.",
      );
    }
    window.addEventListener("reminia:acceso-cortado", onCorte);
    return () => window.removeEventListener("reminia:acceso-cortado", onCorte);
  }, []);

  if (mensaje === null) return null;

  async function pagar() {
    setError(null);
    setPagando(true);
    try {
      const { url } = await crearCheckoutSuscripcion();
      window.location.assign(url);
    } catch {
      setError("No se pudo abrir el pago. Inténtalo de nuevo en un momento.");
      setPagando(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Acceso en pausa"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(18, 49, 46, 0.55)",
        backdropFilter: "blur(3px)",
        display: "grid",
        placeItems: "center",
        padding: 20,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 460,
          background: colors.white,
          border: `1px solid ${colors.sand}`,
          borderRadius: radius.lg,
          padding: "30px 28px",
          boxShadow: shadow.soft,
          textAlign: "center",
        }}
      >
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 14 }}>
          <Logo size={40} textSize={30} />
        </div>
        <h1 style={{ fontSize: 23, marginBottom: 8 }}>El acceso está en pausa</h1>
        <p style={{ color: colors.textMuted, fontSize: 15, lineHeight: 1.55, marginBottom: 22 }}>
          {mensaje}
        </p>

        {isAdmin ? (
          <>
            <Button onClick={pagar} disabled={pagando} style={{ width: "100%" }}>
              {pagando ? "Abriendo el pago…" : "Activar suscripción (pagar)"}
            </Button>
            {error && (
              <p role="alert" style={{ color: colors.coralDeep, fontSize: 13.5, marginTop: 10 }}>
                {error}
              </p>
            )}
            <p style={{ color: colors.textFaint, fontSize: 13, marginTop: 14, lineHeight: 1.5 }}>
              Tus datos y los de las personas se conservan. Al pagar, todo vuelve a
              funcionar al instante.
            </p>
          </>
        ) : (
          <p style={{ color: colors.textMuted, fontSize: 14.5, lineHeight: 1.55 }}>
            Pídele al <strong>administrador del centro</strong> que renueve la suscripción.
            Tus datos se conservan mientras tanto.
          </p>
        )}

        <button
          type="button"
          onClick={signOut}
          style={{
            marginTop: 18,
            background: "transparent",
            border: "none",
            color: colors.sageDark,
            fontWeight: 600,
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}
