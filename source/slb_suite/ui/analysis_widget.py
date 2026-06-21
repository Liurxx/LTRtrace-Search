"""Analysis widget: charts and statistics."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QGridLayout, QTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np

from slb_suite.db.loader import get_stats, get_all_stats


class AnalysisWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._species: str = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Title
        title = QLabel("SoloLTR Distribution Analysis")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Chart area
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

    def set_species(self, species: str):
        if species == self._species:
            return
        self._species = species
        self._update_charts()

    def _update_charts(self):
        self.figure.clear()

        if not self._species:
            self.canvas.draw_idle()
            return

        # Chart 1: CEN vs Arm comparison for current species
        ax1 = self.figure.add_subplot(2, 2, 1)
        stats = get_stats(self._species)
        categories = ["CEN", "PeriCEN", "Arm"]
        values = [
            stats.get("cen_ltr", 0),
            stats.get("pericen_ltr", 0),
            stats.get("arm_ltr", 0),
        ]
        colors = ["#2196F3", "#FF9800", "#9E9E9E"]
        bars = ax1.bar(categories, values, color=colors, edgecolor="white")
        ax1.set_title(f"{self._species} — CEN vs Arm SoloLTR Count")
        ax1.set_ylabel("SoloLTR Count")
        for bar, val in zip(bars, values):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                     str(val), ha="center", va="bottom", fontsize=9)

        # Chart 2: Multi-species comparison
        ax2 = self.figure.add_subplot(2, 2, 2)
        all_stats = get_all_stats()
        sp_names = [s["species"] for s in all_stats]
        total_counts = [s["total_ltr"] for s in all_stats]

        y_pos = range(len(sp_names))
        ax2.barh(y_pos, total_counts, color="#4CAF50", edgecolor="white")
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(sp_names, fontsize=8)
        ax2.set_title("Total SoloLTRs by Species")
        ax2.set_xlabel("Count")
        ax2.invert_yaxis()

        # Chart 3: Superfamily distribution (current species)
        ax3 = self.figure.add_subplot(2, 2, 3)
        self._plot_superfamily_distribution(ax3)

        # Chart 4: Summary stats table
        ax4 = self.figure.add_subplot(2, 2, 4)
        ax4.axis("off")

        total = stats.get("total_ltr", 0)
        cen = stats.get("cen_ltr", 0)
        pericen = stats.get("pericen_ltr", 0)
        arm = stats.get("arm_ltr", 0)
        cen_pct = (cen / total * 100) if total > 0 else 0
        pericen_pct = (pericen / total * 100) if total > 0 else 0
        arm_pct = (arm / total * 100) if total > 0 else 0

        summary_text = f"""
        {self._species} Summary:
        ──────────────────────────
        Total SoloLTRs:     {total:>10,}
        CEN SoloLTRs:       {cen:>10,}  ({cen_pct:.1f}%)
        PeriCEN SoloLTRs:   {pericen:>10,}  ({pericen_pct:.1f}%)
        Arm SoloLTRs:       {arm:>10,}  ({arm_pct:.1f}%)
        ──────────────────────────
        Total Species:  {len(all_stats)}
        """
        ax4.text(0.1, 0.5, summary_text, fontfamily="monospace",
                 fontsize=11, va="center", transform=ax4.transAxes)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_superfamily_distribution(self, ax):
        from slb_suite.utils.config import LTR_DB_PATH
        import sqlite3
        from collections import Counter

        try:
            conn = sqlite3.connect(LTR_DB_PATH)
            rows = conn.execute(
                """SELECT target_ltr_id
                   FROM ltr_insertions
                   WHERE species=? AND region='Centromere'""",
                (self._species,),
            ).fetchall()
            conn.close()

            # Derive superfamily from target_ltr_id: text between first and second "_"
            counter: Counter[str] = Counter()
            for (tid,) in rows:
                if not tid:
                    counter["Unknown"] += 1
                    continue
                parts = tid.split("_")
                if len(parts) >= 2:
                    family = parts[1]
                else:
                    family = tid

                if family == "Still_Unclassified":
                    family = "Unclassified"
                counter[family] += 1

            top10 = counter.most_common(10)
            if top10:
                families = [t[0] for t in top10]
                counts = [t[1] for t in top10]
                colors = plt_colors = [
                    "#E91E63", "#9C27B0", "#673AB7", "#3F51B5", "#2196F3",
                    "#009688", "#4CAF50", "#FF9800", "#FF5722", "#795548",
                ]
                ax.bar(range(len(families)), counts, color=colors[:len(families)])
                ax.set_xticks(range(len(families)))
                ax.set_xticklabels(families, rotation=45, ha="right", fontsize=8)
                ax.set_title(f"{self._species} — Top CEN SoloLTR Superfamilies")
                ax.set_ylabel("Count")
            else:
                ax.text(0.5, 0.5, "No superfamily data", transform=ax.transAxes,
                        ha="center", va="center")
        except Exception:
            ax.text(0.5, 0.5, "Error loading data", transform=ax.transAxes,
                    ha="center", va="center")
