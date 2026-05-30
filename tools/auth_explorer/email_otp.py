#!/usr/bin/env python3
"""
Lector de códigos 2FA de PPI desde un inbox Outlook/Hotmail via IMAP.

Uso:
    from email_otp import wait_for_code
    code = wait_for_code("tu@outlook.com", "app-password")
"""

import email as _email_lib
import email.message
import imaplib
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

# Archivo donde el orquestador externo puede depositar el código 2FA
CODE_FILE = Path("/tmp/ppi_2fa_code.txt")

IMAP_HOST = "imap-mail.outlook.com"
IMAP_PORT = 993

# Carpetas a revisar en orden (PPI puede caer en Junk)
_FOLDERS = ["INBOX", "Junk", "Junk Email", "Spam"]

# Patrones para extraer el código del body del email
_CODE_PATTERNS = [
    r'\b([0-9]{6})\b',                           # 6 dígitos standalone
    r'c[oó]digo[^0-9]{0,10}([0-9]{4,8})',        # "código: XXXXXX"
    r'verification[^0-9]{0,10}([0-9]{4,8})',
    r'code[^0-9]{0,10}([0-9]{4,8})',
    r'token[^0-9]{0,10}([0-9]{4,8})',
]


def wait_for_code(
    email_addr: str,
    app_password: str,
    max_wait: int = 120,
    poll_interval: int = 5,
) -> str:
    """Espera hasta `max_wait` segundos a que llegue el código 2FA de PPI.

    Raises:
        TimeoutError: si no llega el código en el tiempo máximo.
        imaplib.IMAP4.error: si las credenciales IMAP son inválidas.
    """
    # Buscamos emails recibidos desde hace 5 min (margen amplio por diferencias de reloj)
    since = datetime.now() - timedelta(minutes=5)
    deadline = time.time() + max_wait

    while time.time() < deadline:
        code = _scan_inbox(email_addr, app_password, since)
        if code:
            print(f"  [email_otp] Código encontrado: {code}")
            return code
        remaining = int(deadline - time.time())
        print(f"  [email_otp] Esperando código 2FA... ({remaining}s)")
        time.sleep(poll_interval)

    raise TimeoutError(f"No llegó el código 2FA en {max_wait}s. Revisá el email manualmente.")


def _scan_inbox(email_addr: str, app_password: str, since: datetime) -> str | None:
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as conn:
            conn.login(email_addr, app_password)

            for folder in _FOLDERS:
                status, _ = conn.select(folder)
                if status != "OK":
                    continue

                since_str = since.strftime("%d-%b-%Y")
                _, msg_ids_raw = conn.search(None, f"SINCE {since_str}")
                if not msg_ids_raw or not msg_ids_raw[0]:
                    continue

                # Revisamos los últimos 15 emails, del más reciente al más viejo
                msg_ids = msg_ids_raw[0].split()
                for msg_id in reversed(msg_ids[-15:]):
                    _, data = conn.fetch(msg_id, "(RFC822)")
                    if not data or not data[0]:
                        continue
                    raw = data[0][1]
                    msg = _email_lib.message_from_bytes(raw)
                    body = _get_body(msg)
                    code = _find_code(body)
                    if code:
                        return code
    except imaplib.IMAP4.error:
        raise  # credenciales inválidas → propagar para que el caller lo maneje
    except Exception as e:
        print(f"  [email_otp] Error IMAP: {e}")
    return None


def _get_body(msg: _email_lib.message.Message) -> str:
    parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        parts.append(payload.decode("utf-8", errors="replace"))
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                parts.append(payload.decode("utf-8", errors="replace"))
        except Exception:
            pass
    return "\n".join(parts)


def wait_for_code_from_file(max_wait: int = 180, poll_interval: int = 2) -> str:
    """Espera a que aparezca un código 2FA en CODE_FILE.
    El orquestador externo (Claude, script, etc.) escribe el código ahí.
    """
    CODE_FILE.unlink(missing_ok=True)  # limpiar código viejo
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if CODE_FILE.exists():
            code = CODE_FILE.read_text().strip()
            CODE_FILE.unlink(missing_ok=True)
            if code:
                print(f"  [2FA] Código recibido: {code}", flush=True)
                return code
        remaining = int(deadline - time.time())
        print(f"  [2FA] Esperando código en {CODE_FILE} ... ({remaining}s)", flush=True)
        time.sleep(poll_interval)
    raise TimeoutError(f"No llegó el código 2FA en {max_wait}s.")


def _find_code(text: str) -> str | None:
    for pattern in _CODE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


# ── Smoke test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from pathlib import Path

    def _load_env(path: Path) -> None:
        if not path.exists():
            return
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    _load_env(Path(__file__).parent.parent.parent / ".env")

    em = os.environ.get("IMAP_EMAIL", "")
    pw = os.environ.get("IMAP_APP_PASSWORD", "")

    if not em or not pw or "xxxx" in pw:
        print("Configurá IMAP_EMAIL e IMAP_APP_PASSWORD en .env antes de correr este script.")
    else:
        print(f"Conectando a {IMAP_HOST} como {em} ...")
        try:
            code = wait_for_code(em, pw, max_wait=30, poll_interval=5)
            print(f"Código: {code}")
        except TimeoutError as e:
            print(f"Timeout: {e}")
        except imaplib.IMAP4.error as e:
            print(f"Error de autenticación IMAP: {e}")
