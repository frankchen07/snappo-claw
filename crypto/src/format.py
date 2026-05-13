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

    eco = d.get("ecological_framework")
    if eco:
        ps = eco.get("price_structure", {})
        rm = eco.get("range_metrics", {})
        pat = eco.get("pattern", {})
        stg = eco.get("stage", {})

        def _fmt_price(v):
            return f"${v:,.0f}" if v is not None else "N/A"

        lines += [
            "",
            "### Ecological Framework",
            "",
            "**Price Structure**",
            (
                f"- MAs: 10={_fmt_price(ps.get('ma10'))}"
                f"  50={_fmt_price(ps.get('ma50'))}"
                f"  150={_fmt_price(ps.get('ma150'))}"
                f"  200={_fmt_price(ps.get('ma200'))}"
            ),
            f"- RS vs BTC: {ps.get('rs_value', 'N/A')} ({ps.get('rs_interpretation', 'N/A')}, {ps.get('rs_trend', 'N/A')})",
        ]
        if ps.get("support"):
            lines.append(f"- Support: {', '.join(_fmt_price(s) for s in ps['support'])}")
        if ps.get("resistance"):
            lines.append(f"- Resistance: {', '.join(_fmt_price(r) for r in ps['resistance'])}")

        lines += [
            "",
            "**Range Metrics**",
            f"- Closing range: {rm.get('closing_range_pct', 'N/A')}% ({str(rm.get('closing_range_class', 'N/A')).replace('_', ' ')})",
            f"- ATR trend: {rm.get('atr_trend', 'N/A')}",
            "",
            "**Pattern**",
            f"- {pat.get('primary', 'none')} (quality {pat.get('quality', 'N/A')}/10)",
            "",
            f"**Stage {stg.get('stage', '?')}: {stg.get('label', '')}** (confidence: {stg.get('confidence', 'N/A')}%)",
            "",
            "**Expectations**",
            eco.get("expectations", ""),
        ]

        if eco.get("data_notes"):
            lines.append("")
            lines.append("_Notes: " + "; ".join(eco["data_notes"]) + "_")

    lines += [
        "",
        f"*{d['disclaimer']}*",
    ]

    return "\n".join(lines)
