"""Three-panel PNG chart generation for crypto analysis."""

from datetime import datetime, timedelta, timezone


class ChartGenerator:
    def generate(
        self,
        symbol: str,
        prices: list[float],
        volumes: list[float],
        moving_averages: dict[str, float | None],
        rs_line_values: list[float],
        stage: int = 0,
        stage_label: str = "",
        support: list[float] | None = None,
        resistance: list[float] | None = None,
    ) -> str:
        """Generate a 3-panel chart PNG and return the file path."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            raise ImportError("matplotlib required — pip install matplotlib")

        support = support or []
        resistance = resistance or []
        n = len(prices)
        now = datetime.now(timezone.utc)
        dates = [now - timedelta(days=n - i) for i in range(n)]

        def _cumulative_ma(p: list[float], period: int) -> list[float | None]:
            return [
                statistics.mean(p[max(0, i - period):i + 1]) if i >= period - 1 else None
                for i in range(len(p))
            ]

        import statistics
        ma10 = _cumulative_ma(prices, 10)
        ma50 = _cumulative_ma(prices, 50)
        ma200 = _cumulative_ma(prices, 200)

        vol_colors = [
            "#26a69a" if i == 0 or prices[i] >= prices[i - 1] else "#ef5350"
            for i in range(len(volumes))
        ]
        avg_vol = sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 0

        fig, axes = plt.subplots(3, 1, figsize=(12, 9), gridspec_kw={"height_ratios": [3, 1.5, 1.5]})
        fig.patch.set_facecolor("#1a1a2e")

        title = f"{symbol.upper()} — {now.strftime('%Y-%m-%d')}"
        if stage:
            title += f" | Stage {stage}: {stage_label}"
        fig.suptitle(title, color="#e0e0e0", fontsize=13, fontweight="bold")

        for ax in axes:
            ax.set_facecolor("#16213e")
            ax.tick_params(colors="#9e9e9e", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#424242")

        # Panel 1: Price + MAs
        ax1 = axes[0]
        ax1.plot(dates, prices, color="#e0e0e0", linewidth=1.2, label="Price")

        ma_styles = [
            (ma10, "#ffeb3b", 0.8, "10 SMA"),
            (ma50, "#42a5f5", 0.9, "50 SMA"),
            (ma200, "#ef5350", 1.0, "200 SMA"),
        ]
        for ma_vals, color, lw, lbl in ma_styles:
            pts = [(d, v) for d, v in zip(dates, ma_vals) if v is not None]
            if pts:
                ax1.plot([p[0] for p in pts], [p[1] for p in pts], color=color, linewidth=lw, label=lbl, alpha=0.85)

        for s in support:
            ax1.axhline(y=s, color="#26a69a", linewidth=0.7, linestyle="--", alpha=0.7)
        for r in resistance:
            ax1.axhline(y=r, color="#ef5350", linewidth=0.7, linestyle="--", alpha=0.7)

        ax1.set_ylabel("Price (USD)", color="#9e9e9e", fontsize=9)
        ax1.legend(loc="upper left", fontsize=7, facecolor="#1a1a2e", labelcolor="#e0e0e0", framealpha=0.8)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

        # Panel 2: Volume
        ax2 = axes[1]
        ax2.bar(dates, volumes, color=vol_colors, alpha=0.8)
        ax2.axhline(y=avg_vol, color="#ffeb3b", linewidth=0.8, linestyle="-", alpha=0.7, label="20d avg")
        ax2.set_ylabel("Volume", color="#9e9e9e", fontsize=9)
        ax2.legend(loc="upper left", fontsize=7, facecolor="#1a1a2e", labelcolor="#e0e0e0", framealpha=0.8)
        ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{x/1e9:.1f}B" if x >= 1e9 else f"{x/1e6:.0f}M")
        )

        # Panel 3: RS Line
        ax3 = axes[2]
        if rs_line_values:
            rs_dates = dates[-len(rs_line_values):]
            ax3.plot(rs_dates, rs_line_values, color="#ce93d8", linewidth=1.0, label="RS vs BTC")
            ax3.axhline(y=1.0, color="#9e9e9e", linewidth=0.7, linestyle="--", alpha=0.7)
        else:
            ax3.text(0.5, 0.5, "RS data unavailable", ha="center", va="center",
                     transform=ax3.transAxes, color="#9e9e9e")
        ax3.set_ylabel("RS vs BTC", color="#9e9e9e", fontsize=9)
        handles, labels = ax3.get_legend_handles_labels()
        if handles:
            ax3.legend(handles, labels, loc="upper left", fontsize=7, facecolor="#1a1a2e", labelcolor="#e0e0e0", framealpha=0.8)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax3.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=30, ha="right")

        plt.tight_layout()

        out_path = f"/tmp/crypto_chart_{symbol.upper()}.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return out_path
