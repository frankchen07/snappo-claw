"""Unit tests for ExpectationsNarrative."""

import pytest
from crypto.src.narrative import ExpectationsNarrative


def _gen(stage=2, label="Advancing", setup="VCP", rs="strong",
         cr="buyers_winning", atr="stable", support=None, resistance=None):
    en = ExpectationsNarrative()
    return en.generate(
        stage=stage,
        stage_label=label,
        setup_type=setup,
        rs_interpretation=rs,
        closing_range_class=cr,
        atr_trend=atr,
        support_levels=support or [],
        resistance_levels=resistance or [],
    )


class TestExpectationsNarrative:
    def test_returns_non_empty_string(self):
        assert len(_gen()) > 10

    def test_stage2_vcp_strong_rs_mentions_stage2(self):
        result = _gen(stage=2, setup="VCP", rs="strong")
        assert "Stage 2" in result

    def test_stage1_consolidation(self):
        result = _gen(stage=1, label="Consolidation", setup="none")
        assert "Stage 1" in result or "consolidation" in result.lower()

    def test_stage3_distribution(self):
        result = _gen(stage=3, label="Distribution", setup="none", rs="weak")
        assert "Stage 3" in result or "distribution" in result.lower()

    def test_stage4_decline(self):
        result = _gen(stage=4, label="Decline", setup="none", rs="weak")
        assert "Stage 4" in result or "decline" in result.lower()

    def test_stage4_with_support_mentions_price(self):
        result = _gen(stage=4, setup="none", support=[42000.0])
        assert "42,000" in result or "42000" in result

    def test_stage2_breakout_no_crash(self):
        result = _gen(stage=2, setup="breakout", rs="neutral", cr="sellers_winning")
        assert isinstance(result, str) and len(result) > 0

    def test_stage2_cup_and_handle(self):
        result = _gen(stage=2, setup="cup_and_handle", rs="strong")
        assert "cup" in result.lower() or "Stage 2" in result

    def test_all_setups_no_exception(self):
        for setup in ("VCP", "breakout", "flat_base", "cup_and_handle", "none"):
            for stage in (1, 2, 3, 4):
                result = _gen(stage=stage, setup=setup)
                assert isinstance(result, str)
