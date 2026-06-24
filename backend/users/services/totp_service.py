"""Servicio de TOTP (RFC 6238) para 2FA.

Wrappea `pyotp` y `qrcode` para que las views no toquen los detalles
del estándar. Provee:
  - generate_secret() — genera un secret base32 random
  - provisioning_uri(secret, username) — devuelve la otpauth:// URI que
    los authenticator apps escanean
  - qr_data_url(uri) — convierte la URI a un PNG base64 inline para
    renderear como <img src="data:image/png;base64,..."/> en el frontend
  - verify(secret, code) — valida un código de 6 dígitos. Tolera ±1
    ventana de 30s para clock skew.
"""

from __future__ import annotations

import base64
from io import BytesIO

import pyotp
import qrcode

# Nombre del issuer mostrado en la app authenticator. Usuario lo ve como
# "SkilTak (walter@email.com)" en la lista de cuentas.
ISSUER = "SkilTak"

# Ventana de tolerancia para clock skew entre server y device del user.
# valid_window=1 acepta el código actual + el anterior + el siguiente
# (±30s). Default de pyotp es 0 (estricto) — bumpamos a 1 porque users
# en mobile pueden tener clock un poco off.
_VALID_WINDOW = 1


def generate_secret() -> str:
    """Genera un secret base32 random (160 bits — recomendado por RFC 4226)."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_name: str) -> str:
    """Devuelve la otpauth:// URI lista para QR.

    `account_name` se muestra al user en la app (typicamente email o
    username). El issuer en cambio es global ("SkilTak").
    """
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=ISSUER)


def qr_data_url(uri: str) -> str:
    """Convierte la otpauth URI a `data:image/png;base64,...`.

    Lo devolvemos como data URL en vez de servir el PNG desde un
    endpoint propio para que el frontend lo embedea inline en un <img>
    sin un fetch extra.
    """
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def verify(secret: str, code: str) -> bool:
    """True si el código (6 dígitos) corresponde al secret en la
    ventana actual ±1. False si el código es vacío/inválido/expirado."""
    if not secret or not code:
        return False
    # Normalizar: stripar espacios que algunos authenticator apps
    # ponen (formato "123 456").
    cleaned = "".join(code.split())
    if not cleaned.isdigit() or len(cleaned) != 6:
        return False
    return pyotp.TOTP(secret).verify(cleaned, valid_window=_VALID_WINDOW)
