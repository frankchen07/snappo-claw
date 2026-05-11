"""Output formatting: dict, JSON, Markdown."""

import json
from crypto.src.models import AnalysisOutput


def to_dict(analysis: AnalysisOutput) -> dict:
    return analysis.model_dump()


def to_json(analysis: AnalysisOutput, indent: int = 2) -> str:
    return json.dumps(to_dict(analysis), indent=indent)


def to_markdown(analysis: AnalysisOutput) -> str:
    d = to_dict(analysis)
    trend = d["market_trend"]
    setup = d["setup"]
    ez = d["entry_zone"]
    sl = d["stop_level"]
    targets = d["targets"]

    lines = [
        f"## {d['symbol']} Analysis — {d['timestamp']}",
        "",
        f"**Trend:** {trend['direction'].capitalize()} ({trend['strength']})",
        f"**Setup:** {setup['type']} | Quality: {setup['quality']}/10",
        f"**Confidence:** {d['confidence_score']}/100",
        "",
        "### Levels",
        f"- Entry zone: ${ez['price']:,.2f}" + (f" [{ez['range'][0]:,.2f} – {ez['range'][1]:,.2f}]" if ez.get('range') else ""),
        f"- Stop: ${sl['price']:,.2f} ({sl.get('invalidation_reason', '')})",
    ]

    for i, t in enumerate(targets, 1):
        lines.append(f"- Target {i}: ${t['price']:,.2f} ({t['rr_ratio']:.1f}R)")

    lines += [
        "",
        f"**Risk/Reward:** {d['risk_reward']:.1f}R",
        "",
        "### Key Signals",
    ]
    for sig in d["key_signals"]:
        lines.append(f"- {sig}")

    lines += [
        "",
        f"*{d['disclaimer']}*",
    ]

    return "\n".join(lines)
