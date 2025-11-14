# utils/auth.py

import json
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
import streamlit as st


# ==========================
# CARGA DE CONFIGURACIÓN
# ==========================

def load_config():
    """
    Carga el archivo data/config.json.
    """
    with open('data/config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


# ==========================
# FECHA ACTUAL (ZONA HORARIA)
# ==========================

def _today_str() -> str:
    """
    Devuelve la fecha de hoy en formato 'YYYY-MM-DD'
    usando la zona horaria America/New_York.
    Ajusta la zona si lo necesitas.
    """
    tz = ZoneInfo("America/New_York")
    return datetime.now(tz).strftime("%Y-%m-%d")


# ==========================
# GENERADOR DE CÓDIGOS
# ==========================

def generate_access_code(email: str, base: str, date_str: str | None = None) -> str:
    """
    Genera el código de acceso diario para un email y una base.

    TOKEN = BASE + SUFIJO_HASH

    donde SUFIJO_HASH = primeros 8 caracteres en mayúsculas de:
        SHA256( base + "|" + date_str + "|" + email_normalizado + "|" + salt )

    - email se normaliza a minúsculas y sin espacios.
    - date_str por defecto es la fecha de hoy 'YYYY-MM-DD' en America/New_York.
    - salt se lee de config["password_salt"].

    Este mismo algoritmo se usa tanto para GENERAR como para VALIDAR.
    """
    config = load_config()
    salt = config.get("password_salt", "")
    if not salt:
        raise ValueError("Configuration error: 'password_salt' is not set in data/config.json")

    if date_str is None:
        date_str = _today_str()

    email_clean = email.strip().lower()
    raw = f"{base}|{date_str}|{email_clean}|{salt}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    suffix = h[:8]  # longitud del sufijo; puedes ajustar si quieres
    return base + suffix


# ==========================
# VERIFICACIÓN DE CONTRASEÑA
# ==========================

def verify_password(token: str, email: str) -> bool:
    """
    Verifica si el 'token' (código de acceso) es válido para el 'email' dado.

    Reglas:
    1) Si token coincide con master_password_full → acceso FULL sin filtros.
    2) Si token coincide con master_password_short → acceso SHORT sin filtros.
    3) En otro caso:
       - Se recalcula el código esperado para cada base FULL con generate_access_code(email, base).
       - Si token == expected para alguna base FULL → acceso FULL.
       - Idem para bases SHORT → acceso SHORT.

    En caso de éxito, establece:
      - st.session_state["exam_type"] = "full" | "short"
    y devuelve True. En caso contrario, devuelve False.
    """
    config = load_config()
    token = token.strip()
    email_clean = email.strip()

    if not token or not email_clean:
        return False

    # ====================================
    # 1) CLAVES MAESTRAS (sin filtros)
    # ====================================
    master_full = config.get("master_password_full")
    master_short = config.get("master_password_short")

    if master_full and token == master_full:
        st.session_state["exam_type"] = "full"
        return True

    if master_short and token == master_short:
        st.session_state["exam_type"] = "short"
        return True

    # ====================================
    # 2) CLAVES DIARIAS POR EMAIL (FULL)
    # ====================================
    for base in config.get("passwords_full_base", []):
        try:
            expected = generate_access_code(email_clean, base)
        except Exception:
            # Si fallara algo en generate_access_code, mejor seguir con el siguiente intento
            continue

        if token == expected:
            st.session_state["exam_type"] = "full"
            return True

    # ====================================
    # 3) CLAVES DIARIAS POR EMAIL (SHORT)
    # ====================================
    for base in config.get("passwords_short_base", []):
        try:
            expected = generate_access_code(email_clean, base)
        except Exception:
            continue

        if token == expected:
            st.session_state["exam_type"] = "short"
            return True

    # Nada coincidió
    return False
