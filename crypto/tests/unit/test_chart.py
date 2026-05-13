"""Unit tests for ChartGenerator — runs with real matplotlib Agg (headless)."""

import os
import pytest


def _prices(n: int = 100, start: float = 50000.0, drift: float = 0.002) -> list[float]:
    p = [start]
    for _ in range(n - 1):
        p.append(p[-1] * (1 + drift))
    return p


def _volumes(n: int = 100, base: float = 1_000_000.0) -> list[float]:
    return [base] * n


@pytest.fixture(autouse=True)
def cleanup_charts():
    """Remove generated chart files after each test."""
    yield
    for fname in os.listdir("/tmp"):
        if fname.startswith("crypto_chart_") and fname.endswith(".png"):
            try:
                os.remove(f"/tmp/{fname}")
            except FileNotFoundError:
                pass


class TestChartGenerator:
    def test_returns_string_path(self):
        from crypto.src.chart import ChartGenerator

        cg = ChartGenerator()
        path = cg.generate(
            symbol="BTC",
            prices=_prices(100),
            volumes=_volumes(100),
            moving_averages={"ma10": 51000.0, "ma50": 50000.0, "ma200": 49000.0},
            rs_line_values=[1.0] * 100,
            stage=2,
            stage_label="Advancing",
        )
        assert isinstance(path, str)
        assert "BTC" in path
        assert path.endswith(".png")

    def test_path_is_tmp_dir(self):
        from crypto.src.chart import ChartGenerator

        cg = ChartGenerator()
        path = cg.generate(
            symbol="ETH",
            prices=_prices(50),
            volumes=_volumes(50),
            moving_averages={},
            rs_line_values=[1.0] * 50,
        )
        assert path.startswith("/tmp/")

    def test_file_is_written_to_disk(self):
        from crypto.src.chart import ChartGenerator

        cg = ChartGenerator()
        path = cg.generate(
            symbol="SOL",
            prices=_prices(100),
            volumes=_volumes(100),
            moving_averages={"ma50": 100.0},
            rs_line_values=[1.0] * 100,
            stage=1,
            stage_label="Consolidation",
        )
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 0

    def test_support_resistance_accepted(self):
        from crypto.src.chart import ChartGenerator

        cg = ChartGenerator()
        path = cg.generate(
            symbol="BTC",
            prices=_prices(100),
            volumes=_volumes(100),
            moving_averages={},
            rs_line_values=[1.0] * 100,
            support=[45000.0, 43000.0],
            resistance=[55000.0, 58000.0],
        )
        assert isinstance(path, str)

    def test_symbol_uppercased_in_path(self):
        from crypto.src.chart import ChartGenerator

        cg = ChartGenerator()
        path = cg.generate(
            symbol="btc",  # lowercase input
            prices=_prices(30),
            volumes=_volumes(30),
            moving_averages={},
            rs_line_values=[1.0] * 30,
        )
        assert "BTC" in path
