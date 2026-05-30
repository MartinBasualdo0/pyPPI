#!/usr/bin/env python3
"""
PPI Auth Explorer — Análisis comparativo de sesiones.

Lee los archivos generados por capture.py y determina qué cookies/headers
usa PPI para reconocer un dispositivo confiable y saltear el 2FA.

Usage:
    python analyze.py
    python analyze.py --output /otra/carpeta
"""

import argparse
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"

# ── Helpers ────────────────────────────────────────────────────────────────────

def load(path: Path) -> dict:
    return json.loads(path.read_text())


def section(title: str, width: int = 60) -> None:
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def cookie_diff(before: dict, after: dict) -> list[dict]:
    findings = []
    for name, c in after.items():
        if name not in before:
            findings.append({
                "type": "NEW",
                "name": name,
                "value": str(c.get("value", ""))[:80],
                "domain": c.get("domain"),
                "expires": c.get("expires"),
                "httpOnly": c.get("httpOnly"),
                "secure": c.get("secure"),
                "sameSite": c.get("sameSite"),
            })
        elif c.get("value") != before[name].get("value"):
            findings.append({
                "type": "CHANGED",
                "name": name,
                "old_value": str(before[name].get("value", ""))[:60],
                "new_value": str(c.get("value", ""))[:60],
                "domain": c.get("domain"),
                "expires": c.get("expires"),
            })
    for name in before:
        if name not in after:
            findings.append({"type": "REMOVED", "name": name})
    return findings


def expires_str(expires) -> str:
    if expires is None or expires == -1 or expires == 0:
        return "session cookie (se pierde al cerrar el browser)"
    try:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(float(expires), tz=timezone.utc)
        return f"expira {dt.strftime('%Y-%m-%d %H:%M UTC')}"
    except Exception:
        return f"expires={expires}"


def print_cookie(c: dict, prefix: str = "  ") -> None:
    exp = expires_str(c.get("expires"))
    print(f"{prefix}● {c['name']}")
    print(f"{prefix}  valor:    {str(c.get('value', ''))[:80]}")
    print(f"{prefix}  {exp}")
    print(f"{prefix}  domain={c.get('domain')}, httpOnly={c.get('httpOnly')}, secure={c.get('secure')}")


def analyze_auth_traffic(captured: list[dict], session_label: str) -> None:
    auth_reqs = [
        e for e in captured
        if e["kind"] == "request" and _is_auth(e.get("path", ""))
    ]
    auth_res = [
        e for e in captured
        if e["kind"] == "response" and _is_auth(e.get("path", ""))
    ]

    print(f"\n  Requests de auth capturados ({len(auth_reqs)}):")
    if not auth_reqs:
        print("    (ninguno)")
    for r in auth_reqs:
        print(f"    [{r['method']}] {r['path']}")
        if r.get("post_data"):
            print(f"           body: {r['post_data'][:120]}")

    # Set-Cookie headers en responses de auth
    set_cookies_seen = []
    for res in auth_res:
        for hname, hval in res.get("headers", {}).items():
            if hname.lower() == "set-cookie":
                set_cookies_seen.append((res["path"], hval))

    if set_cookies_seen:
        print(f"\n  Set-Cookie headers en responses de auth:")
        for path, val in set_cookies_seen:
            print(f"    {path}")
            print(f"      → {val[:140]}")


def _is_auth(path: str) -> bool:
    p = path.lower()
    return any(k in p for k in ("login", "2fa", "auth", "token", "seguridad", "refresh"))


# ── Main ───────────────────────────────────────────────────────────────────────

def main(output_dir: Path) -> None:
    s1_file = output_dir / "session1.json"
    s2_file = output_dir / "session2.json"

    if not s1_file.exists():
        print(f"\nNo se encontró {s1_file}. Corré capture.py primero.")
        return

    s1 = load(s1_file)
    s2 = load(s2_file) if s2_file.exists() else None

    print("\n" + "=" * 60)
    print("  PPI Auth Explorer — Análisis de mecanismo de confianza")
    print("=" * 60)

    # ── Sesión 1 ──────────────────────────────────────────────────────────
    section("SESIÓN 1 — Login completo con 2FA")
    print(f"  2FA solicitado: {'SÍ' if s1['twofa_called'] else 'NO'}")

    c1_before: dict = s1["checkpoints"]["before_login"]["cookies"]
    c1_after: dict  = s1["checkpoints"]["after_login"]["cookies"]

    diff1 = cookie_diff(c1_before, c1_after)
    new1  = [d for d in diff1 if d["type"] == "NEW"]
    mod1  = [d for d in diff1 if d["type"] == "CHANGED"]

    print(f"\n  Cookies nuevas tras el login ({len(new1)}):")
    if not new1:
        print("    (ninguna — llamativo, puede que ya estuvieran)")
    for d in new1:
        print_cookie({**d, "value": d["value"]}, prefix="    ")

    if mod1:
        print(f"\n  Cookies modificadas ({len(mod1)}):")
        for d in mod1:
            print(f"    ~ {d['name']}: {d['old_value'][:40]} → {d['new_value'][:40]}")

    analyze_auth_traffic(s1["captured"], "sesión 1")

    # localStorage / sessionStorage
    ls = s1["checkpoints"]["after_login"].get("storage", {}).get("localStorage", {})
    ss = s1["checkpoints"]["after_login"].get("storage", {}).get("sessionStorage", {})
    if ls:
        print(f"\n  localStorage post-login ({len(ls)} keys):")
        for k, v in ls.items():
            print(f"    {k}: {str(v)[:100]}")
    if ss:
        print(f"\n  sessionStorage post-login ({len(ss)} keys):")
        for k, v in ss.items():
            print(f"    {k}: {str(v)[:100]}")

    if not s2:
        print("\n  No hay sesión 2 para comparar. Corré capture.py completo.")
        return

    # ── Sesión 2 ──────────────────────────────────────────────────────────
    section("SESIÓN 2 — Re-login con cookies de sesión 1 restauradas")
    print(f"  2FA solicitado: {'SÍ' if s2['twofa_called'] else 'NO'}")

    c2_before: dict = s2["checkpoints"]["before_login"]["cookies"]
    c2_after: dict  = s2["checkpoints"]["after_login"]["cookies"]

    print(f"\n  Cookies restauradas al inicio ({len(c2_before)}):")
    for name in c2_before:
        print(f"    {name}")

    analyze_auth_traffic(s2["captured"], "sesión 2")

    # ── Análisis comparativo ──────────────────────────────────────────────
    section("ANÁLISIS COMPARATIVO")

    # Cookies seteadas por PPI durante sesión 1 (presentes en after pero no en before)
    ppi_set_in_s1 = set(c1_after.keys()) - set(c1_before.keys())
    # De esas, cuáles llegaron correctamente a la sesión 2
    restored_ok    = ppi_set_in_s1 & set(c2_before.keys())
    missing_in_s2  = ppi_set_in_s1 - set(c2_before.keys())

    print(f"\n  Cookies seteadas por PPI en sesión 1: {len(ppi_set_in_s1)}")
    for name in ppi_set_in_s1:
        c = c1_after[name]
        indicator = "✓" if name in restored_ok else "✗ (falta en s2)"
        print(f"    {indicator} {name} — {expires_str(c.get('expires'))}")

    if missing_in_s2:
        print(f"\n  Cookies que PPI seteó pero NO se restauraron en sesión 2:")
        for name in missing_in_s2:
            c = c1_after.get(name, {})
            exp = expires_str(c.get("expires"))
            print(f"    ✗ {name} ({exp})")
            if "session" in exp:
                print(f"       ^ Esta es una session cookie: no persiste al cerrar el browser.")

    # ── Veredicto ─────────────────────────────────────────────────────────
    section("VEREDICTO")

    if not s2["twofa_called"]:
        print("  ✓ Sesión 2 NO pidió 2FA — las cookies restauradas funcionan.\n")
        print("  Las cookies responsables del trust son:")
        for name in restored_ok:
            c = c2_before.get(name, {})
            print_cookie(c, prefix="    ")
        print()
        print("  Acción recomendada para pyPPI:")
        print("  → Estas cookies hay que persistirlas en el archivo de sesión.")
        session_cookies = [
            name for name in restored_ok
            if c1_after.get(name, {}).get("expires") in (None, -1, 0, "")
        ]
        if session_cookies:
            print(f"\n  OJO: estas son session cookies (sin expires permanente): {session_cookies}")
            print("  requests.Session las guarda en memoria pero no en disco.")
            print("  pyPPI ya las persiste en JSON — verificar que se restauren correctamente.")

    else:
        print("  ✗ Sesión 2 SÍ pidió 2FA — las cookies solas no alcanzan.\n")
        print("  Posibles causas:")
        if missing_in_s2:
            print(f"  1. Cookies faltantes que PPI necesita: {list(missing_in_s2)}")
            session_missing = [
                name for name in missing_in_s2
                if c1_after.get(name, {}).get("expires") in (None, -1, 0, "")
            ]
            if session_missing:
                print(f"     De estas, son session cookies (sin persistencia): {session_missing}")
        print("  2. PPI usa fingerprinting adicional (User-Agent, IP, etc.)")
        print("  3. La cookie de confianza expiró entre sesiones")
        print("  4. El endpoint de 2FA requiere un header device-id calculado en JS")

        # Buscar headers custom en requests de s1 para pistas de fingerprinting
        auth_reqs_s1 = [
            e for e in s1["captured"]
            if e["kind"] == "request" and _is_auth(e.get("path", ""))
        ]
        if auth_reqs_s1:
            # Buscar headers no-estándar
            standard = {"host", "content-type", "accept", "origin", "referer", "user-agent",
                        "accept-encoding", "accept-language", "connection", "content-length",
                        "authorization", "cookie"}
            custom_headers: dict[str, set] = {}
            for req in auth_reqs_s1:
                for hname in req.get("headers", {}):
                    if hname.lower() not in standard:
                        custom_headers.setdefault(hname, set()).add(req["path"])
            if custom_headers:
                print("\n  Headers custom encontrados en requests de auth (posibles device-ids):")
                for hname, paths in custom_headers.items():
                    print(f"    {hname}  (en: {', '.join(paths)})")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analiza sesiones capturadas por capture.py")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Carpeta con session*.json")
    args = parser.parse_args()
    main(args.output)
