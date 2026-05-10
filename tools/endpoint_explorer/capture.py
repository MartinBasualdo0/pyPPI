#!/usr/bin/env python3
"""
Playwright manual capture tool.

Opens a headed Chromium browser so you can navigate portfoliopersonal.com
manually. Every API call to api.portfoliopersonal.com is intercepted and
saved to captured_endpoints.db. Close the browser window when done.

Usage:
    python capture.py
    python capture.py --ticker DNC3
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import Response, async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from db import get_stats, init_db, save_endpoint

API_HOST = "api.portfoliopersonal.com"
HOME_URL = "https://cuenta.portfoliopersonal.com"
MAX_BODY_BYTES = 50_000

# Skip auth endpoints — they contain credentials in the request body
SKIP_PATHS = {
    "/api/Seguridad/Auth/Login",
    "/api/Seguridad/Auth/ValidateUser2FA",
}


async def handle_response(response: Response, stats: dict) -> None:
    if API_HOST not in response.url:
        return

    request = response.request
    if request.method == "OPTIONS":
        return

    from urllib.parse import urlparse
    path = urlparse(request.url).path
    if path in SKIP_PATHS:
        return

    try:
        raw = await response.body()
        body = raw[:MAX_BODY_BYTES].decode("utf-8", errors="replace")
    except Exception:
        body = None

    endpoint = {
        "url": request.url,
        "method": request.method,
        "request_headers": json.dumps(dict(request.headers)),
        "request_body": request.post_data,
        "response_status": response.status,
        "response_body": body,
    }

    is_new = save_endpoint(endpoint)
    if is_new:
        stats["new"] += 1
        short_path = path + ("?…" if "?" in request.url else "")
        print(f"  [NEW] {request.method:6s} {short_path}")
    else:
        stats["duplicate"] += 1


async def main(ticker: str | None) -> None:
    init_db()
    stats = {"new": 0, "duplicate": 0}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        page.on(
            "response",
            lambda r: asyncio.create_task(handle_response(r, stats)),
        )

        await page.goto(HOME_URL)

        print("\nBrowser listo en portfoliopersonal.com")
        if ticker:
            print(f"Tip: buscá el ticker '{ticker}' en la sección de mercado/bonos.")
        print("Navegá libremente. Cerrá el browser cuando termines.\n")

        done = asyncio.Event()
        context.on("close", lambda: done.set())
        browser.on("disconnected", lambda: done.set())

        await done.wait()

    print("\nCaptura finalizada.")
    print(f"  Endpoints nuevos capturados: {stats['new']}")
    print(f"  Duplicados ignorados:        {stats['duplicate']}")
    s = get_stats()
    print(f"  Total en DB:                 {s['total']}")
    print(f"\nCorré analyze.py para clasificarlos con Claude.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Captura endpoints de PPI navegando manualmente"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="Ticker de referencia (ej: DNC3). Solo muestra un hint, no navega solo.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.ticker))
