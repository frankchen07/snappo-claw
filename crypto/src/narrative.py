"""Rule-based forward-looking narrative for each stage+setup combination."""


class ExpectationsNarrative:
    _SETUP_DESC = {
        "VCP": "a volatility contraction pattern coiling for breakout",
        "breakout": "a confirmed breakout above prior resistance",
        "flat_base": "a tight flat base suggesting accumulation",
        "cup_and_handle": "a cup-and-handle with handle near the highs",
        "none": "no clear setup pattern",
    }

    _RS_DESC = {
        "strong": "RS outpacing BTC",
        "weak": "RS lagging BTC",
        "neutral": "RS roughly in line with BTC",
    }

    def generate(
        self,
        stage: int,
        stage_label: str,
        setup_type: str,
        rs_interpretation: str,
        closing_range_class: str,
        atr_trend: str,
        support_levels: list[float],
        resistance_levels: list[float],
    ) -> str:
        setup_desc = self._SETUP_DESC.get(setup_type, "no clear setup")
        rs_desc = self._RS_DESC.get(rs_interpretation, "RS neutral")
        res_note = f" at ${resistance_levels[0]:,.0f}" if resistance_levels else ""
        sup_note = f" at ${support_levels[0]:,.0f}" if support_levels else ""
        buyers = "buyers" in closing_range_class
        atr_note = "Volatility expanding — expect wider swings." if atr_trend == "expanding" else "Volatility coiling — breakout potential building."

        if stage == 2:
            if setup_type in ("VCP", "flat_base", "cup_and_handle"):
                if rs_interpretation == "strong":
                    return (
                        f"Stage 2 uptrend with {setup_desc}; {rs_desc} — favorable if volume expands on the break. "
                        f"Watch for continuation above resistance{res_note}."
                    )
                return (
                    f"Stage 2 structure intact with {setup_desc}, though {rs_desc} — monitor RS improvement before sizing up. "
                    f"{atr_note}"
                )
            if setup_type == "breakout":
                return (
                    f"Breaking out in Stage 2 with {rs_desc}; {closing_range_class.replace('_', ' ')} — "
                    f"{'hold above the breakout level.' if buyers else 'wait for a close above resistance before adding.'}"
                )
            return (
                f"Stage 2 uptrend, no actionable pattern yet; {rs_desc}. "
                f"{'ATR expanding — expect increased volatility.' if atr_trend == 'expanding' else 'Wait for a base to form before entry.'}"
            )

        if stage == 1:
            return (
                f"Stage 1 consolidation — no directional edge. {rs_desc.capitalize()}. "
                f"{'A breakout above the base on volume would signal Stage 2.' if setup_type in ('VCP', 'flat_base', 'cup_and_handle') else 'Watch for a base to develop before looking for entry.'}"
            )

        if stage == 3:
            return (
                f"Stage 3 distribution — uptrend aging. {rs_desc.capitalize()}. "
                f"{'Sellers gaining control — defensive posture warranted.' if not buyers else 'Reduce exposure; avoid new longs until trend confirms.'}"
            )

        if stage == 4:
            return (
                f"Stage 4 decline — avoid long entries. {rs_desc.capitalize()}. "
                f"Next key support{sup_note if support_levels else ' not identified — price discovery mode'}."
            )

        return f"Stage {stage} {stage_label} — insufficient data for a specific narrative."
