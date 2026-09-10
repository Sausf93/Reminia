"""Configuración de la aplicación, leída del entorno (.env)."""
import hashlib
import hmac
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_JWT_SECRET_DEV = "dev-secret-cambiar"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Entorno: "dev" | "prod". En prod se exige un JWT_SECRET propio (ver validador).
    entorno: str = "dev"

    # Base de datos
    database_url: str = "postgresql+asyncpg://trazo:trazo@localhost:5432/trazo"
    # SSL para Postgres gestionado (Aiven/Supabase/etc. lo exigen). asyncpg NO
    # entiende ?sslmode= en la URL, así que se activa con este flag: DB_SSL=true.
    db_ssl: bool = False

    # JWT
    jwt_secret: str = _JWT_SECRET_DEV
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # CORS (cadena separada por comas)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Comportamiento de arranque. La siembra de datos de DEMO (que crea cuentas
    # con contraseña conocida) solo debe ocurrir en dev: además de este flag, el
    # arranque exige entorno == "dev" para sembrar (ver main.py). Así un
    # despliegue de producción no queda con credenciales de demo aunque olvide
    # apagar el flag.
    seed_on_startup: bool = True
    app_timezone: str = "Europe/Madrid"

    # Token de PLATAFORMA (nivel 0): protege el alta de centros + su primer admin
    # (POST /plataforma/centros). Si está vacío, ese endpoint queda DESHABILITADO.
    # Solo lo conoce el dueño de la plataforma (tú). Nunca se expone al panel.
    platform_token: str = ""

    # Token del banco de pruebas de contenido (cabecera X-Lab-Token). VACÍO por
    # defecto: ya NO hay un valor público en el repo. Si no se fija un BANCO_TOKEN
    # propio por entorno, se DERIVA del JWT_SECRET (ver `lab_token`). Sin datos de
    # personas.
    banco_token: str = ""

    # --- Stripe (facturación por suscripción). Si stripe_secret_key está vacío,
    # el cobro queda DESACTIVADO (útil en dev/tests: no se llama a Stripe). ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""  # precio con tramos (125€/30 + 3€) creado en Stripe
    # URL del panel del centro, para las redirecciones de Stripe Checkout.
    panel_url: str = "https://trazo-panel.pages.dev"

    # --- Correo transaccional (Resend). Si resend_api_key está vacío, el envío
    # queda DESACTIVADO (se registra en log y NO rompe el alta). ---
    resend_api_key: str = ""
    resend_from: str = "Reminia <onboarding@resend.dev>"
    # URL pública de la landing (para enlaces en los correos de alta).
    landing_url: str = "https://trazo-web-af2.pages.dev"
    # Correo del dueño de la plataforma (tú): recibe un aviso en cada alta nueva.
    # Vacío = no se avisa. Se define como variable de entorno PLATAFORMA_EMAIL.
    plataforma_email: str = ""

    @property
    def correo_activo(self) -> bool:
        return bool(self.resend_api_key)

    @property
    def stripe_activo(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_price_id)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def lab_token(self) -> str:
        """Token efectivo del banco (X-Lab-Token). Seguro y DINÁMICO: si no se fija
        un BANCO_TOKEN explícito por entorno, se DERIVA del JWT_SECRET con HMAC. Así
        nunca es un valor público del repo, es único por entorno (en prod el
        JWT_SECRET ya es un secreto propio) y no hay que configurar nada aparte."""
        if self.banco_token:
            return self.banco_token
        return hmac.new(self.jwt_secret.encode(), b"banco-veredictos",
                        hashlib.sha256).hexdigest()

    @model_validator(mode="after")
    def _exigir_secreto_en_prod(self) -> "Settings":
        """Fail-fast: en producción NO se arranca con el secreto JWT por defecto.

        Evita firmar tokens con un secreto público conocido (falsificación de
        credenciales de cualquier staff/centro). En dev se permite el default.
        """
        if self.entorno.lower() != "dev" and self.jwt_secret == _JWT_SECRET_DEV:
            raise ValueError(
                "JWT_SECRET no definido: en producción (ENTORNO!=dev) debes fijar "
                "un secreto propio en el entorno."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
