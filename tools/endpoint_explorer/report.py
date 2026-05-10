#!/usr/bin/env python3
"""
Generates a markdown report from analyzed endpoints.

Usage:
    python report.py              # writes report.md and prints summary
    python report.py --stdout     # prints report to stdout only
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import get_all, get_stats

OUTPUT_PATH = Path(__file__).parent / "report.md"
RESPONSE_PREVIEW_CHARS = 1_500
HEADERS_PREVIEW_CHARS = 800

SCORE_LABEL = {2: "★★ Muy útil", 1: "★ Posiblemente útil", 0: "— No relevante"}


def _fmt_headers(headers_json: str | None) -> str:
    if not headers_json:
        return "(sin headers)"
    try:
        headers = json.loads(headers_json)
        skip = {
            "accept-encoding", "accept-language", "cache-control", "connection",
            "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest", "sec-fetch-user",
            "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "pragma",
            "upgrade-insecure-requests",
        }
        filtered = {k: v for k, v in headers.items() if k.lower() not in skip}
        text = json.dumps(filtered, indent=2, ensure_ascii=False)
    except Exception:
        text = headers_json
    if len(text) > HEADERS_PREVIEW_CHARS:
        text = text[:HEADERS_PREVIEW_CHARS] + "\n… (truncado)"
    return text


def _truncate(text: str | None, max_len: int) -> str:
    if not text:
        return "(vacío)"
    if len(text) > max_len:
        return text[:max_len] + f"\n… ({len(text)} chars total, truncado)"
    return text


def _endpoint_section(ep: dict) -> str:
    lines = []
    score = ep.get("relevance_score", 0) or 0
    lines.append(f"### `{ep['method']} {ep['path']}`\n")
    lines.append(f"- **Relevancia:** {SCORE_LABEL.get(score, '?')} — {ep.get('relevance_reason', '')}")
    lines.append(f"- **Cobertura:** {ep.get('coverage_notes', '')}\n")
    lines.append("**URL completa:**")
    lines.append("```")
    lines.append(ep["url"])
    lines.append("```\n")
    if ep.get("request_body"):
        lines.append("**Request body:**")
        lines.append("```json")
        lines.append(_truncate(ep["request_body"], RESPONSE_PREVIEW_CHARS))
        lines.append("```\n")
    lines.append("**Headers relevantes:**")
    lines.append("```json")
    lines.append(_fmt_headers(ep.get("request_headers")))
    lines.append("```\n")
    lines.append("**Respuesta (muestra):**")
    lines.append("```json")
    lines.append(_truncate(ep.get("response_body"), RESPONSE_PREVIEW_CHARS))
    lines.append("```\n")
    lines.append("---\n")
    return "\n".join(lines)


def generate_report(endpoints: list[dict]) -> str:
    stats = get_stats()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_relevant = sorted(
        [e for e in endpoints if (e.get("relevance_score") or 0) >= 1 and e.get("coverage_status") == "NEW"],
        key=lambda e: e.get("relevance_score") or 0,
        reverse=True,
    )
    covered = [e for e in endpoints if e.get("coverage_status") == "COVERED"]
    not_relevant = [e for e in endpoints if (e.get("relevance_score") or 0) == 0 and e.get("coverage_status") == "NEW"]
    unanalyzed = [e for e in endpoints if e.get("relevance_score") is None]

    lines = [
        "# Endpoint Explorer — Reporte\n",
        f"_Generado: {now}_\n",
        f"**Capturados:** {stats['total']} &nbsp;|&nbsp; "
        f"**Analizados:** {stats['analyzed']} &nbsp;|&nbsp; "
        f"**Nuevos relevantes:** {stats['new_relevant']}\n",
        "---\n",
        f"## 1. Endpoints nuevos y relevantes ({len(new_relevant)})\n",
    ]

    if not new_relevant:
        lines.append("_Ninguno encontrado todavía. Navegá más secciones y volvé a correr analyze.py._\n")
    else:
        for ep in new_relevant:
            lines.append(_endpoint_section(ep))

    lines += [
        f"## 2. Endpoints ya cubiertos en pyPPI ({len(covered)})\n",
    ]
    if not covered:
        lines.append("_Ninguno._\n")
    else:
        for ep in covered:
            lines.append(f"- `{ep['method']} {ep['path']}` — {ep.get('coverage_notes', '')}")
        lines.append("")

    lines += [
        f"\n## 3. Endpoints descartados — no relevantes ({len(not_relevant)})\n",
    ]
    if not not_relevant:
        lines.append("_Ninguno._\n")
    else:
        for ep in not_relevant:
            lines.append(f"- `{ep['method']} {ep['path']}` — {ep.get('relevance_reason', '')}")
        lines.append("")

    if unanalyzed:
        lines += [
            f"\n## 4. Sin analizar ({len(unanalyzed)})\n",
            "_Corré `analyze.py` para clasificarlos._\n",
        ]
        for ep in unanalyzed:
            lines.append(f"- `{ep['method']} {ep['path']}`")

    return "\n".join(lines)


def main(to_stdout: bool = False) -> None:
    endpoints = get_all()
    if not endpoints:
        print("No hay endpoints capturados. Corré capture.py primero.")
        sys.exit(1)

    report = generate_report(endpoints)

    if to_stdout:
        print(report)
    else:
        OUTPUT_PATH.write_text(report, encoding="utf-8")
        s = get_stats()
        print(f"Reporte generado: {OUTPUT_PATH}")
        print(f"  Nuevos relevantes: {s['new_relevant']}")
        print(f"  Total capturados:  {s['total']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera reporte markdown de endpoints analizados")
    parser.add_argument("--stdout", action="store_true", help="Imprimir en stdout en lugar de escribir report.md")
    args = parser.parse_args()
    main(to_stdout=args.stdout)
