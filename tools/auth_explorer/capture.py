#!/usr/bin/env python3
"""
PPI Auth Explorer — Bot de captura 100% autónomo.

Flujo:
  Sesión 1 → login completo con 2FA (código leído del email via IMAP)
  Sesión 2 → re-login con las cookies de sesión 1 restauradas
             (debería saltear el 2FA si las cookies son suficientes)

Requiere en .env:
    PPI_USER          — usuario PPI (ej: martinbas98)
    PPI_PASSWORD      — contraseña PPI
    IMAP_EMAIL        — email donde llega el código 2FA
    IMAP_APP_PASSWORD — App Password de Outlook/Hotmail

Usage:
    python capture.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, Response, async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from email_otp import CODE_FILE, wait_for_code, wait_for_code_from_file

HOME_URL = "https://cuenta.portfoliopersonal.com"
API_HOST = "api.portfoliopersonal.com"
OUTPUT_DIR = Path(__file__).parent / "output"

_AUTH_PATHS = ("/Auth/Login", "/Auth/ValidateUser2FA", "/Auth/RefreshToken")


# ── .env loader ───────────────────────────────────────────────────────────────

def _load_env() -> None:
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_auth(path: str) -> bool:
    return any(p in path for p in _AUTH_PATHS)


def _mask(raw: str | None) -> str | None:
    if not raw:
        return raw
    try:
        obj = json.loads(raw)
        for k in ("clave", "password", "codigo", "refreshToken", "accessToken"):
            if k in obj:
                obj[k] = "***"
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return raw


async def _cookies_snapshot(ctx: BrowserContext) -> dict:
    return {c["name"]: c for c in await ctx.cookies()}


async def _storage_snapshot(page: Page) -> dict:
    try:
        return await page.evaluate("""() => ({
            localStorage:   Object.fromEntries(Object.entries(localStorage)),
            sessionStorage: Object.fromEntries(Object.entries(sessionStorage)),
        })""")
    except Exception:
        return {"localStorage": {}, "sessionStorage": {}}


# ── Form interaction ──────────────────────────────────────────────────────────

async def _fill_login_form(page: Page, user: str, password: str) -> None:
    user_selectors = [
        'input[name="usuario"]', 'input[name="user"]', 'input[name="username"]',
        'input[name="email"]',   'input[type="email"]',
        'input[placeholder*="suario" i]', 'input[placeholder*="mail" i]',
    ]
    for sel in user_selectors:
        try:
            await page.fill(sel, user, timeout=2_000)
            print(f"  [form] usuario → {sel}")
            break
        except Exception:
            pass

    await page.fill('input[type="password"]', password, timeout=5_000)
    print("  [form] contraseña completada")

    for sel in ['button[type="submit"]', 'button:has-text("Ingres")', 'button:has-text("Inici")']:
        try:
            await page.click(sel, timeout=2_000)
            print(f"  [form] submit → {sel}")
            return
        except Exception:
            pass
    await page.keyboard.press("Enter")
    print("  [form] submit → Enter")


async def _fill_2fa_form(page: Page, code: str) -> None:
    # Esperar a que la SPA renderice el formulario de 2FA
    try:
        await page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    await page.wait_for_timeout(1_500)

    print(f"  [2FA] URL: {page.url}", flush=True)

    # Screenshot para diagnóstico
    screenshot_path = OUTPUT_DIR / "2fa_page.png"
    await page.screenshot(path=str(screenshot_path))
    print(f"  [debug] Screenshot guardado → {screenshot_path}", flush=True)

    # Log de todos los inputs presentes
    all_inputs = await page.query_selector_all("input")
    print(f"  [debug] {len(all_inputs)} inputs en la página:", flush=True)
    for i, inp in enumerate(all_inputs):
        attrs = {}
        for attr in ("type", "name", "id", "placeholder", "maxlength", "autocomplete", "inputmode"):
            v = await inp.get_attribute(attr)
            if v:
                attrs[attr] = v[:60]
        vis = await inp.is_visible()
        print(f"    [{i}] visible={vis} {attrs}", flush=True)

    filled = False

    # 1. Split OTP con inputmode="numeric" (caso PPI: position1..position6)
    #    Locator.press_sequentially dispara eventos de teclado reales,
    #    activando el auto-avance JS de PPI entre inputs.
    numeric_loc = page.locator('input[inputmode="numeric"]')
    numeric_count = await numeric_loc.count()
    if numeric_count >= len(code):
        await numeric_loc.first.click()
        await numeric_loc.first.press_sequentially(code, delay=80)
        print(f"  [form] código 2FA → press_sequentially en {numeric_count} inputs numeric", flush=True)
        filled = True

    if not filled:
        # 2. Split OTP con maxlength="1"
        digit_loc = page.locator('input[maxlength="1"]')
        digit_count = await digit_loc.count()
        if digit_count >= len(code):
            await digit_loc.first.click()
            await digit_loc.first.press_sequentially(code, delay=80)
            print(f"  [form] código 2FA → press_sequentially en {digit_count} inputs maxlength=1", flush=True)
            filled = True

    if not filled:
        # 3. Input único (código en un solo campo)
        for sel in [
            'input[name="codigo"]', 'input[autocomplete="one-time-code"]',
            'input[maxlength="6"]', 'input[type="number"]',
            'input[placeholder*="digo" i]', 'input[placeholder*="code" i]',
        ]:
            try:
                await page.fill(sel, code, timeout=2_000)
                print(f"  [form] código 2FA → {sel}", flush=True)
                filled = True
                break
            except Exception:
                pass

    if not filled:
        # 4. Fallback amplio: primer input visible no-password
        for inp in all_inputs:
            if not await inp.is_visible():
                continue
            t = (await inp.get_attribute("type") or "text").lower()
            if t not in ("password", "hidden", "submit", "button", "checkbox", "radio"):
                await inp.click()
                await page.keyboard.type(code, delay=80)
                print(f"  [form] código 2FA → keyboard.type fallback (type={t})", flush=True)
                filled = True
                break

    if not filled:
        raise RuntimeError("No se encontró el campo de código 2FA en la página.")

    # Marcar "Es un dispositivo seguro" (recordar=true)
    try:
        cb = await page.query_selector('input[name="recordar"]')
        if cb and not await cb.is_checked():
            await cb.check(timeout=2_000)
            print("  [form] 'Es un dispositivo seguro' marcado", flush=True)
    except Exception:
        pass

    # Enviar
    for sel in [
        'button[type="submit"]', 'button:has-text("Confirm")',
        'button:has-text("Verific")', 'button:has-text("Acept")',
    ]:
        try:
            await page.click(sel, timeout=2_000)
            print(f"  [form] submit 2FA → {sel}")
            return
        except Exception:
            pass
    await page.keyboard.press("Enter")
    print("  [form] submit 2FA → Enter")


# ── Session runner ────────────────────────────────────────────────────────────

async def run_session(
    p,
    session_num: int,
    user: str,
    password: str,
    imap_email: str,
    imap_password: str,
    restore_cookies: list | None = None,
) -> dict:
    print(f"\n{'='*60}")
    print(f"  SESIÓN {session_num}")
    print(f"{'='*60}")

    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )

    if restore_cookies:
        valid = [c for c in restore_cookies if c.get("domain")]
        await context.add_cookies(valid)
        print(f"\n  Cookies restauradas: {len(valid)} cookies")

    # ── Captura de tráfico ────────────────────────────────────────────────
    captured: list[dict] = []
    auth_events: list[dict] = []  # solo eventos de auth con body parseado

    async def on_request(req) -> None:
        if API_HOST not in req.url:
            return
        path = urlparse(req.url).path
        entry = {
            "kind": "request", "url": req.url, "path": path,
            "method": req.method, "headers": dict(req.headers),
            "post_data": _mask(req.post_data),
            "ts": datetime.now().isoformat(),
        }
        captured.append(entry)
        if _is_auth(path):
            print(f"  → [{req.method}] {path}  body={_mask(req.post_data)}")

    async def on_response(res: Response) -> None:
        if API_HOST not in res.url:
            return
        path = urlparse(res.url).path
        all_headers = dict(await res.all_headers())
        entry = {
            "kind": "response", "url": res.url, "path": path,
            "status": res.status, "headers": all_headers,
            "ts": datetime.now().isoformat(),
        }
        if _is_auth(path):
            try:
                raw = await res.body()
                entry["body"] = raw.decode("utf-8", errors="replace")[:8_000]
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {"raw": entry["body"][:200]}
                auth_events.append({"path": path, "status": res.status, "data": data})
            except Exception as e:
                entry["body"] = None
                auth_events.append({"path": path, "status": res.status, "data": {}, "error": str(e)})
            print(f"  ← [{res.status}] {path}")
            for hname, hval in all_headers.items():
                if hname.lower() == "set-cookie":
                    print(f"       Set-Cookie: {hval[:140]}")
        captured.append(entry)

    context.on("request", lambda r: asyncio.create_task(on_request(r)))
    context.on("response", lambda r: asyncio.create_task(on_response(r)))

    page = await context.new_page()

    # Checkpoint 0: antes del login
    snap_before = await _cookies_snapshot(context)
    print(f"\n  Cookies iniciales: {list(snap_before.keys()) or '(ninguna)'}")

    # ── Navegar y hacer login ─────────────────────────────────────────────
    await page.goto(HOME_URL)
    await page.wait_for_load_state("domcontentloaded", timeout=20_000)

    await _fill_login_form(page, user, password)

    # Esperar la respuesta del endpoint de login (hasta 30s)
    login_data = await _wait_for_auth_event(auth_events, "/Auth/Login", timeout=30.0)

    if login_data["status"] != 200 or login_data["data"].get("status") != 0:
        msg = login_data["data"].get("message", "error desconocido")
        await browser.close()
        raise RuntimeError(f"Login fallido: {msg}")

    payload = login_data["data"].get("payload", {})
    twofa_called = False

    # ── 2FA si es necesario ───────────────────────────────────────────────
    if payload.get("twoFAInfo") and not payload.get("token"):
        twofa_called = True
        print(f"\n  2FA requerido (tipo: {payload['twoFAInfo'].get('twoFactorType')})")

        # Intentar IMAP si está configurado; si falla, esperar código por archivo
        _placeholders = ("xxxx", "tu@", "your@", "example")
        imap_ok = imap_email and imap_password and not any(
            p in v for p in _placeholders for v in (imap_email, imap_password)
        )

        code = None
        if imap_ok:
            print("  Leyendo código del email via IMAP...", flush=True)
            try:
                code = await asyncio.get_event_loop().run_in_executor(
                    None, wait_for_code, imap_email, imap_password
                )
            except Exception as e:
                print(f"  IMAP falló ({e}). Usando fallback por archivo.", flush=True)

        if code is None:
            print(f"WAITING_FOR_2FA_CODE", flush=True)
            print(f"  Escribí el código 2FA en: {CODE_FILE}", flush=True)
            code = await asyncio.get_event_loop().run_in_executor(
                None, wait_for_code_from_file
            )

        await _fill_2fa_form(page, code)

        # Esperar que la URL salga de la página de 2FA (más robusto que esperar el API event)
        print("  Esperando redirección post-2FA...", flush=True)
        try:
            await page.wait_for_url(
                lambda url: "twoFactor" not in url,
                timeout=30_000,
            )
            print(f"  2FA validado — URL: {page.url}", flush=True)
        except Exception:
            # Si la URL no cambió, puede que la validación falló — screenshot para diagnóstico
            shot = OUTPUT_DIR / "2fa_after_submit.png"
            await page.screenshot(path=str(shot))
            # Revisar si llegó algún evento de error en auth_events
            twofa_events = [e for e in auth_events if "ValidateUser2FA" in e.get("path", "")]
            if twofa_events:
                last = twofa_events[-1]
                msg = last.get("data", {}).get("message", str(last))
                await browser.close()
                raise RuntimeError(f"2FA rechazado por PPI: {msg}")
            await browser.close()
            raise RuntimeError(f"2FA timeout — URL no cambió. Screenshot: {shot}")

        print("  2FA completado correctamente", flush=True)
    else:
        print("  Login directo sin 2FA")

    # Esperar a que la SPA navegue al dashboard
    await _wait_for_dashboard(page, timeout=30.0)

    # Checkpoint 1: después del login
    snap_after = await _cookies_snapshot(context)
    storage = await _storage_snapshot(page)
    cookies_raw = await context.cookies()

    await browser.close()

    print(f"\n  2FA solicitado: {'SÍ' if twofa_called else 'NO'}")
    print(f"  Requests capturados: {len([e for e in captured if e['kind'] == 'request'])}")
    print(f"  Cookies post-login:  {len(snap_after)}")

    return {
        "session": session_num,
        "twofa_called": twofa_called,
        "cookies_raw": cookies_raw,
        "checkpoints": {
            "before_login": {"cookies": snap_before},
            "after_login":  {"cookies": snap_after, "storage": storage},
        },
        "captured": captured,
    }


# ── Event helpers ─────────────────────────────────────────────────────────────

async def _wait_for_auth_event(
    events: list[dict], path_keyword: str, timeout: float
) -> dict:
    """Espera a que aparezca en `events` un entry cuyo path contenga `path_keyword`."""
    deadline = asyncio.get_event_loop().time() + timeout
    seen = 0
    while asyncio.get_event_loop().time() < deadline:
        for i in range(seen, len(events)):
            if path_keyword in events[i]["path"]:
                return events[i]
        seen = len(events)
        await asyncio.sleep(0.3)
    raise TimeoutError(f"No se recibió respuesta de {path_keyword} en {timeout}s")


async def _wait_for_dashboard(page: Page, timeout: float) -> None:
    """Espera a que la URL salga de la pantalla de login."""
    login_url = page.url
    try:
        await page.wait_for_function(
            "startUrl => window.location.href !== startUrl",
            arg=login_url,
            timeout=int(timeout * 1_000),
        )
        print(f"  Dashboard alcanzado: {page.url}")
    except Exception:
        # Si no cambia la URL, igual continuamos (puede ser SPA sin cambio de ruta)
        print(f"  (URL no cambió, asumiendo dashboard: {page.url})")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    _load_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    user     = os.environ.get("PPI_USER", "")
    password = os.environ.get("PPI_PASSWORD", "")
    imap_em  = os.environ.get("IMAP_EMAIL", "")
    imap_pw  = os.environ.get("IMAP_APP_PASSWORD", "")

    _placeholders = ("xxxx", "tu@", "your@", "example")
    missing = [k for k, v in {
        "PPI_USER": user, "PPI_PASSWORD": password,
        "IMAP_EMAIL": imap_em, "IMAP_APP_PASSWORD": imap_pw,
    }.items() if not v or any(p in v for p in _placeholders)]

    if missing:
        print(f"\nFaltan variables de entorno en .env: {missing}")
        print("Completá el .env antes de correr este script.")
        return

    print("\nPPI Auth Explorer — Bot autónomo")
    print(f"  PPI user:   {user}")
    print(f"  IMAP email: {imap_em}")
    print("=" * 60)

    async with async_playwright() as p:

        # ── Sesión 1: login completo con 2FA ──────────────────────────────
        session1 = await run_session(
            p, session_num=1,
            user=user, password=password,
            imap_email=imap_em, imap_password=imap_pw,
        )
        out1 = OUTPUT_DIR / "session1.json"
        out1.write_text(json.dumps(session1, indent=2, ensure_ascii=False, default=str))
        print(f"\n  Sesión 1 guardada → {out1}")

        # ── Sesión 2: re-login con cookies de sesión 1 ────────────────────
        print("\n  Iniciando sesión 2 con cookies de sesión 1 restauradas...")
        session2 = await run_session(
            p, session_num=2,
            user=user, password=password,
            imap_email=imap_em, imap_password=imap_pw,
            restore_cookies=session1["cookies_raw"],
        )
        out2 = OUTPUT_DIR / "session2.json"
        out2.write_text(json.dumps(session2, indent=2, ensure_ascii=False, default=str))
        print(f"\n  Sesión 2 guardada → {out2}")

    print("\n  Captura finalizada. Corré analyze.py para el análisis.")


if __name__ == "__main__":
    asyncio.run(main())
