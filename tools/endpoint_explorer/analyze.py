#!/usr/bin/env python3
"""
Batch analysis of captured endpoints using Claude.

Two agents per endpoint:
  1. Relevance agent — scores 0/1/2 based on financial analysis value.
  2. Coverage agent  — checks if the endpoint is already in pyPPI.

Usage:
    ANTHROPIC_API_KEY=sk-... python analyze.py
    ANTHROPIC_API_KEY=sk-... python analyze.py --reanalyze   # re-run all
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent))
from db import get_all, get_stats, get_unanalyzed, update_analysis

MODEL = "claude-sonnet-4-6"
RESPONSE_SAMPLE_CHARS = 2_000

# ── Context shared across all calls (good candidate for prompt caching) ───────

EXISTING_ENDPOINTS = """\
endpoints = {
    "token":               "api/Seguridad/Auth/Login",
    "validate_2fa":        "api/Seguridad/Auth/ValidateUser2FA",
    "cuenta_ID":           "/api/Cuenta/ComitentesAsignados",
    "refresh_token":       "/api/Seguridad/Auth/RefreshToken",
    "ticker_search":       "/api/Cotizaciones/Item/Search?q={}",
    "ranking":             "/api/Cotify/Ranking",
    "bonds_groups":        "/api/Cotizaciones/Bono/PorGrupo?id=13463",
    "tickers_list":        "/api/Ordenes/InstrumentosOperables?cuentaID={}&tipoProducto={}&tipoOperacion={}&tipoPlazoLiquidacion={}",
    "technical_data_bonds":"/api/Cotizaciones/Bono/{}/DatosTecnicos?plazoLiquidacionID={}",
    "historic_data":       "/api/Cotizaciones/Item/{}/Historico/{}?fechaDesde={}&fechaHasta={}",
    "intraday_data":       "/api/Cotizaciones/Item/{}/Intradiario?idPlazo={}",
}

Public methods in the PPI class:
- get_tickers_list(instrument_type, operation_type, settlement)
- search_tickers(short_ticker, item_id)
- get_technical_data_bonds(settlement, item_id)
- get_historic_data(item_id, settlement, date_from, date_to)
- get_intraday_data(item_id, settlement)
"""

SYSTEM_PROMPT = """\
Sos un analista de APIs financieras. Tu tarea es evaluar endpoints de la API \
privada de Portfolio Personal (broker argentino) para determinar si son útiles \
para análisis de activos financieros argentinos (bonos, ONs, acciones) y si ya \
están implementados en la librería pyPPI.

Respondé SIEMPRE con un JSON válido y nada más."""


def _build_user_prompt(ep: dict) -> str:
    response_sample = (ep.get("response_body") or "")[:RESPONSE_SAMPLE_CHARS]
    return f"""\
Analiza este endpoint capturado de la API de Portfolio Personal:

URL:    {ep["url"]}
Método: {ep["method"]}
Status: {ep.get("response_status")}
Respuesta (muestra):
{response_sample}

---
Endpoints YA implementados en pyPPI:
{EXISTING_ENDPOINTS}

Respondé con este JSON (sin texto adicional):
{{
  "relevance_score": <0, 1 o 2>,
  "relevance_reason": "<una oración breve>",
  "coverage_status": "<COVERED o NEW>",
  "coverage_notes": "<una oración breve>"
}}

Criterios relevance_score:
  0 = No útil para análisis financiero (telemetría, UI, notificaciones, auth)
  1 = Posiblemente útil (datos del instrumento distintos de precios/histórico)
  2 = Muy útil (CUIT del emisor, datos legales, calificaciones, prospecto,
      información de la empresa emisora, flujos de pagos, amortizaciones)

Criterios coverage_status:
  COVERED = El path de este endpoint ya está en los endpoints de pyPPI
            (aunque los parámetros sean distintos)
  NEW     = El path NO está cubierto por ningún endpoint existente"""


def analyze_endpoint(client: anthropic.Anthropic, ep: dict) -> tuple[int, str, str, str]:
    """Returns (relevance_score, relevance_reason, coverage_status, coverage_notes)."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(ep)}],
    )
    text = response.content[0].text.strip()
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        result = json.loads(text[start:end])
        return (
            int(result["relevance_score"]),
            str(result["relevance_reason"]),
            str(result["coverage_status"]),
            str(result["coverage_notes"]),
        )
    except Exception as exc:
        return (0, f"Error al parsear respuesta de Claude: {exc}", "NEW", "—")


def main(reanalyze: bool = False) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY no está configurada en el entorno.")
        sys.exit(1)

    if reanalyze:
        endpoints = get_all()
    else:
        endpoints = get_unanalyzed()

    if not endpoints:
        print("No hay endpoints pendientes de análisis.")
        s = get_stats()
        print(f"Total: {s['total']} | Analizados: {s['analyzed']} | Nuevos relevantes: {s['new_relevant']}")
        return

    client = anthropic.Anthropic(api_key=api_key)
    total = len(endpoints)
    print(f"Analizando {total} endpoint{'s' if total != 1 else ''}...\n")

    for i, ep in enumerate(endpoints, 1):
        label = f"[{i}/{total}]"
        short = f"{ep['method']:6s} {ep['path']}"
        print(f"{label} {short}", end=" ... ", flush=True)

        score, reason, coverage, notes = analyze_endpoint(client, ep)
        update_analysis(ep["id"], score, reason, coverage, notes)

        icon = ["—", "~", "★"][min(score, 2)]
        print(f"{icon} score={score} | {coverage:7s} | {reason[:70]}")

    print()
    s = get_stats()
    print("Análisis completo.")
    print(f"  Total endpoints:              {s['total']}")
    print(f"  Analizados:                   {s['analyzed']}")
    print(f"  Nuevos y relevantes (score≥1): {s['new_relevant']}")
    print("\nCorré report.py para ver el reporte completo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analiza endpoints capturados con Claude")
    parser.add_argument(
        "--reanalyze",
        action="store_true",
        help="Re-analizar todos los endpoints, incluso los ya clasificados",
    )
    args = parser.parse_args()
    main(reanalyze=args.reanalyze)
