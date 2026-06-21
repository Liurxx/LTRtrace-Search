"""Genome Browser — JBrowse 2 style, optimized with PatchCollection + dynamic LOD."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QSplitter, QTextEdit, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.collections import PatchCollection
import numpy as np

from slb_suite.db.loader import (
    get_chromosomes, get_ltrs_for_chromosome,
    get_chromosome_length, get_all_chromosome_lengths,
    get_cen_bed_regions,
)
from slb_suite.utils.config import SUPERFAMILY_COLORS, DEFAULT_SF_COLOR, REGION_TRACK_COLORS

# ── JBrowse 2 palette ─────────────────────────────────────────────────────
JB_BG         = "#FFFFFF"
JB_TRACK_BG   = "#FAFAFA"
JB_GRID       = "#F0F0F0"
JB_RULER_BG   = "#F5F5F5"
JB_RULER_LINE = "#424242"
JB_RULER_TICK = "#9E9E9E"
JB_TRACK_BORDER = "#E0E0E0"
JB_TEXT       = "#212121"
JB_TEXT_MUTED = "#757575"
JB_CEN_COLOR  = "#1976D2"
JB_PERICEN_COLOR = "#F57C00"
JB_ARM_COLOR  = "#BDBDBD"
JB_DENSITY_FILL = "#90CAF9"
JB_DENSITY_LINE = "#1E88E5"

# ── LOD thresholds ─────────────────────────────────────────────────────────
LOD_FEATURE_THRESHOLD = 3_000_000   # show individual features if view < 3 Mb
LOD_DETAIL_THRESHOLD  = 500_000     # show feature borders if view < 500 kb

# ── Track dimensions ───────────────────────────────────────────────────────
TRACK_H     = 0.95
TRACK_GAP   = 0.30
DENSITY_ROW = 0.95
FEATURE_ROW = 2.20
REGION_ROW  = 3.45
RULER_ROW   = 4.70
CHART_TOP   = 5.10


class GenomeCanvas(FigureCanvasQTAgg):
    """High-performance canvas with PatchCollection rendering and dynamic LOD."""

    ltr_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(15, 5.5), dpi=100, facecolor=JB_BG)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(380)

        self._species = ""
        self._chr = ""
        self._chr_len = 1
        self._ltrs: list[dict] = []
        self._density_y: np.ndarray = None
        self._density_x: np.ndarray = None

        # View state
        self.v0 = 0       # view_start
        self.v1 = 1       # view_end

        # Pre-computed region spans
        self._arm_spans: list[tuple[int, int]] = []
        self._pericen_spans: list[tuple[int, int]] = []
        self._cen_spans: list[tuple[int, int]] = []

        # Interaction state
        self._pan_start = None
        self._pan_v0 = None

        # Events
        self.fig.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.fig.canvas.mpl_connect("button_press_event", self._on_press)
        self.fig.canvas.mpl_connect("button_release_event", self._on_release)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.fig.canvas.mpl_connect("pick_event", self._on_pick)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── Public API ─────────────────────────────────────────────────────────

    def load(self, species: str, chr_name: str, ltrs: list[dict]):
        self._species = species
        self._chr = chr_name
        self._chr_len = get_chromosome_length(species, chr_name) or max(
            (r.get("end", 0) for r in ltrs), default=1)
        self._ltrs = ltrs
        self._cen_bed = get_cen_bed_regions(species)
        self.v0, self.v1 = 0, self._chr_len
        self._precompute()
        self._draw()

    def zoom(self, factor: float):
        span = self.v1 - self.v0
        center = (self.v0 + self.v1) / 2
        new_span = max(min(span * factor, self._chr_len), 2000)
        self.v0 = max(0, int(center - new_span / 2))
        self.v1 = min(self._chr_len, int(center + new_span / 2))
        self._draw()

    def pan(self, fraction: float):
        span = self.v1 - self.v0
        shift = int(span * fraction)
        self.v0 = max(0, self.v0 + shift)
        if self.v0 + span > self._chr_len:
            self.v0 = max(0, self._chr_len - span)
        self.v1 = self.v0 + span
        self._draw()

    def full_view(self):
        self.v0, self.v1 = 0, self._chr_len
        self._draw()

    def jump_to(self, pos: int):
        span = self.v1 - self.v0
        half = span // 2
        self.v0 = max(0, pos - half)
        self.v1 = min(self._chr_len, pos + half)
        self._draw()

    def view_range(self) -> tuple[int, int]:
        return self.v0, self.v1

    # ── Pre-computation ────────────────────────────────────────────────────

    def _precompute(self):
        """One-time pre-computation for the chromosome."""
        if not self._ltrs:
            return

        arr = np.array([(r["start"], r.get("region_code", 0)) for r in self._ltrs])
        positions = arr[:, 0]

        # Density: 1000-bin histogram
        bins = np.linspace(0, self._chr_len, 1001)
        self._density_y, edges = np.histogram(positions, bins=bins)
        self._density_x = (edges[:-1] + edges[1:]) / 2
        self._density_y = self._density_y.astype(float)
        self._density_y[self._density_y > 0] = np.log2(
            self._density_y[self._density_y > 0] + 1)

        # Region spans: pre-compute per region type
        for code, name, store in [
            (0, "Arm", "arm"),
            (1, "Pericentromere", "pericen"),
            (2, "Centromere", "cen"),
        ]:
            mask = arr[:, 1] == code
            if not mask.any():
                setattr(self, f"_{store}_spans", [])
                continue
            pos = np.sort(positions[mask])
            spans = []
            s = pos[0]; e = pos[0]
            for p in pos[1:]:
                if p - e > 5_000_000:
                    spans.append((int(s), int(e)))
                    s = p
                e = p
            spans.append((int(s), int(e)))
            setattr(self, f"_{store}_spans", spans)

    # ── Drawing ────────────────────────────────────────────────────────────

    def _draw(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_xlim(self.v0, self.v1)
        ax.set_ylim(0, CHART_TOP)

        view_span = self.v1 - self.v0
        show_features = view_span < LOD_FEATURE_THRESHOLD

        # Background
        ax.set_facecolor(JB_BG)

        # ── Track backgrounds ──
        track_defs = [
            (0, DENSITY_ROW, TRACK_H, "Density"),
            (DENSITY_ROW + TRACK_GAP, FEATURE_ROW, TRACK_H, "SoloLTR"),
            (FEATURE_ROW + TRACK_GAP, REGION_ROW, TRACK_H, "Region"),
        ]
        for y0, y1, h, _ in track_defs:
            rect = Rectangle((self.v0, y0), view_span, h,
                             facecolor=JB_TRACK_BG, edgecolor=JB_TRACK_BORDER,
                             linewidth=0.5, zorder=0)
            ax.add_patch(rect)

        # ── Ruler ──
        self._ruler(ax)

        # ── Track 1: Density ──
        self._density(ax)

        # ── Track 2: Features ──
        if show_features:
            self._features(ax)
        else:
            ax.text(self.v0 + view_span * 0.02, FEATURE_ROW + TRACK_H / 2,
                    "Zoom in (< 3 Mb) to see individual LTR features",
                    fontsize=9, color=JB_TEXT_MUTED, va="center")

        # ── Track 3: Region annotation ──
        self._regions(ax)

        # ── Track labels ──
        for y0, y1, h, label in track_defs:
            ax.text(self.v0 + view_span * 0.008, y0 + h * 0.5, label,
                    fontsize=9, fontweight="bold", color=JB_TEXT_MUTED,
                    va="center", zorder=10)

        # ── Chromosome label ──
        ax.set_title(
            f"{self._species}  ·  {self._chr}  ·  {self.v0:,} – {self.v1:,} bp  ·  {view_span:,} bp span",
            fontsize=10, fontweight="normal", color=JB_TEXT,
            family="monospace", pad=6, loc="center")

        # ── Styling ──
        ax.yaxis.set_visible(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(axis="x", labelsize=8, colors=JB_TEXT_MUTED)
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"{x/1e6:.1f} Mb" if x >= 1e6 else f"{x/1e3:.0f} kb"))
        ax.grid(axis="x", color=JB_GRID, linewidth=0.5, alpha=0.5)
        ax.tick_params(axis="x", which="both", bottom=False, top=False)

        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.06)
        self.draw_idle()

    def _ruler(self, ax):
        """Clean coordinate ruler at the top."""
        y = RULER_ROW
        ax.hlines(y, self.v0, self.v1, color=JB_RULER_LINE, linewidth=1.5, zorder=5)

        span = self.v1 - self.v0
        if span > 10_000_000:
            major = 10_000_000; minor = 2_000_000
        elif span > 2_000_000:
            major = 2_000_000; minor = 500_000
        elif span > 500_000:
            major = 500_000; minor = 100_000
        elif span > 100_000:
            major = 100_000; minor = 20_000
        elif span > 10_000:
            major = 10_000; minor = 2_000
        else:
            major = max(span // 8, 100); minor = max(span // 40, 20)

        # Minor ticks
        t0 = (self.v0 // minor) * minor
        for p in range(int(t0), int(self.v1) + 1, int(minor)):
            if p < self.v0: continue
            ax.vlines(p, y - 0.12, y, color=JB_RULER_TICK, linewidth=0.4, zorder=5)

        # Major ticks
        t0 = (self.v0 // major) * major
        for p in range(int(t0), int(self.v1) + 1, int(major)):
            if p < self.v0: continue
            ax.vlines(p, y - 0.22, y, color=JB_RULER_LINE, linewidth=1.0, zorder=5)
            lbl = f"{p/1e6:.1f} Mb" if p >= 1e6 else f"{p/1e3:.0f} kb"
            ax.text(p, y - 0.30, lbl, fontsize=7, color=JB_TEXT, ha="center", zorder=5)

    def _density(self, ax):
        """Density histogram as a single filled area."""
        if self._density_y is None:
            return
        mask = (self._density_x >= self.v0) & (self._density_x <= self.v1)
        if not mask.any():
            return
        x = self._density_x[mask]
        y = self._density_y[mask]
        base = DENSITY_ROW
        y_norm = y / max(y.max(), 1) * TRACK_H * 0.9
        ax.fill_between(x, base, base + y_norm, color=JB_DENSITY_FILL,
                        edgecolor="none", alpha=0.8, zorder=2, linewidth=0)
        ax.plot(x, base + y_norm, color=JB_DENSITY_LINE, linewidth=0.6, alpha=0.7, zorder=3)

    def _features(self, ax):
        """LTR features using PatchCollection (single draw call)."""
        view_span = self.v1 - self.v0
        show_borders = view_span < LOD_DETAIL_THRESHOLD

        # Only render features in the visible range
        ltrs = [r for r in self._ltrs
                if r["end"] >= self.v0 and r["start"] <= self.v1]
        if not ltrs:
            return

        # Sort by superfamily for consistent coloring
        by_sf = {}
        for r in ltrs:
            sf = r.get("superfamily", "Unclassified")
            by_sf.setdefault(sf, []).append(r)

        base = FEATURE_ROW
        feat_h = TRACK_H * 0.22
        n_rows = max(1, int(TRACK_H / (feat_h * 2.2)))

        patches = []
        patch_ltrs = []  # parallel list for pick lookup
        row_i = 0
        for sf, items in by_sf.items():
            color = SUPERFAMILY_COLORS.get(sf, DEFAULT_SF_COLOR)
            ry = base + 0.06 + (row_i % n_rows) * (feat_h * 2.0)
            for r in items:
                w = max(r["end"] - r["start"], 2)
                rect = Rectangle((r["start"], ry), w, feat_h,
                                 facecolor=color, edgecolor=color if not show_borders else "#333",
                                 linewidth=0.3 if show_borders else 0,
                                 alpha=0.82, picker=True)
                rect._ltr_data = r
                patches.append(rect)
                patch_ltrs.append(r)
            row_i += 1

        if patches:
            pc = PatchCollection(patches, match_original=True)
            ax.add_collection(pc)
            # Store reference so pick event can find patches
            self._patch_ltrs = patch_ltrs

    def _regions(self, ax):
        """Region annotation with colored blocks (legend rendered externally).
        CEN BED precise boundaries are rendered as distinct overlay borders."""
        base = REGION_ROW
        h = TRACK_H
        for spans, color in [
            (self._arm_spans, JB_ARM_COLOR),
            (self._pericen_spans, JB_PERICEN_COLOR),
            (self._cen_spans, JB_CEN_COLOR),
        ]:
            for s, e in spans:
                if e >= self.v0 and s <= self.v1:
                    rect = Rectangle((s, base + 0.08), e - s, h - 0.16,
                                     facecolor=color, edgecolor="none",
                                     alpha=0.45, zorder=1)
                    ax.add_patch(rect)

        # ── CEN BED precise boundaries ──
        cen_bounds = self._cen_bed.get(self._chr)
        if cen_bounds is None and self._cen_bed:
            # Case-insensitive fallback for chr naming differences
            chk = self._chr.lower()
            for k, v in self._cen_bed.items():
                if k.lower() == chk:
                    cen_bounds = v
                    break

        if cen_bounds is not None:
            cs, ce = cen_bounds
            if ce >= self.v0 and cs <= self.v1:
                # CEN BED overlay with dashed border
                rect = Rectangle((cs, base + 0.04), ce - cs, h - 0.08,
                                 facecolor=JB_CEN_COLOR, edgecolor="#0D47A1",
                                 linewidth=1.5, linestyle="--",
                                 alpha=0.35, zorder=4)
                ax.add_patch(rect)
                # Label at center, visible only when zoomed in enough
                mid = (cs + ce) / 2
                view_span = self.v1 - self.v0
                if view_span < 50_000_000:
                    ax.annotate("CEN", xy=(mid, base + h/2),
                               fontsize=7, color="#0D47A1", fontweight="bold",
                               ha="center", va="center",
                               bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                         ec="#0D47A1", alpha=0.85),
                               zorder=6)

    # ── Interaction handlers ───────────────────────────────────────────────

    def _on_scroll(self, event):
        if event.inaxes is None: return
        self.zoom(0.55 if event.button == "up" else 1.8)

    def _on_press(self, event):
        if event.inaxes is None: return
        if event.button == 1:
            self._pan_start = event.xdata
            self._pan_v0 = self.v0
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _on_release(self, event):
        self._pan_start = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_motion(self, event):
        if self._pan_start is None or event.xdata is None: return
        dx = self._pan_start - event.xdata
        span = self.v1 - self.v0
        shift = int(dx / max(span, 1) * span)
        new_start = max(0, self._pan_v0 + shift)
        if new_start + span > self._chr_len:
            new_start = self._chr_len - span
        self.v0 = max(0, new_start)
        self.v1 = self.v0 + span
        self._draw()

    def _on_pick(self, event):
        artist = event.artist
        if hasattr(artist, "_ltr_data"):
            self.ltr_clicked.emit(artist._ltr_data)


# ── Widget ─────────────────────────────────────────────────────────────────

class GenomeBrowserWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._species = ""
        self._chrs: list[str] = []
        self._cache: dict[str, list[dict]] = {}
        self._current_chr = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # ── Canvas (create first so toolbar can reference it) ──
        self.canvas = GenomeCanvas()
        self.canvas.ltr_clicked.connect(self._on_feature_click)

        # ── Toolbar ──
        bar = QHBoxLayout()
        bar.setSpacing(6)

        bar.addWidget(QLabel("Chr:"))
        self.chr_combo = QComboBox()
        self.chr_combo.setMinimumWidth(90)
        self.chr_combo.currentTextChanged.connect(self._on_chr_changed)
        bar.addWidget(self.chr_combo)
        bar.addSpacing(10)

        self.species_lbl = QLabel("")
        self.species_lbl.setFont(QFont("", 11, QFont.Weight.Bold))
        self.species_lbl.setStyleSheet(f"color: {JB_TEXT};")
        bar.addWidget(self.species_lbl)
        bar.addSpacing(15)

        for text, slot, tip in [
            ("−", lambda: self.canvas.zoom(2.0), "Zoom out"),
            ("+", lambda: self.canvas.zoom(0.4), "Zoom in"),
            ("◀", lambda: self.canvas.pan(-0.3), "Pan left"),
            ("▶", lambda: self.canvas.pan(0.3), "Pan right"),
            ("⟲", self.canvas.full_view, "Full chromosome view"),
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(32, 26)
            btn.setToolTip(tip)
            btn.setStyleSheet("""
                QPushButton {
                    background: #E3F2FD; border: 1px solid #90CAF9; border-radius: 3px;
                    font-size: 14px; padding: 0; color: #1565C0;
                }
                QPushButton:hover { background: #BBDEFB; border-color: #64B5F6; }
                QPushButton:pressed { background: #90CAF9; }
            """)
            btn.clicked.connect(slot)
            bar.addWidget(btn)

        bar.addSpacing(15)
        self.range_lbl = QLabel("")
        self.range_lbl.setFont(QFont("monospace", 9))
        self.range_lbl.setStyleSheet(f"color: {JB_TEXT_MUTED};")
        bar.addWidget(self.range_lbl)
        bar.addStretch()
        layout.addLayout(bar)

        # ── Quick chromosome bar ──
        self.chr_bar = QHBoxLayout()
        self.chr_bar.setSpacing(2)
        layout.addLayout(self.chr_bar)

        # ── Region legend bar (outside canvas) ──
        legend_frame = QFrame()
        legend_frame.setFixedHeight(28)
        legend_frame.setStyleSheet(
            f"QFrame {{ background: {JB_BG}; border: 1px solid {JB_TRACK_BORDER}; "
            f"border-radius: 3px; margin: 0px 0px 2px 0px; }}"
        )
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(12, 2, 12, 2)
        legend_layout.setSpacing(16)
        legend_layout.addWidget(QLabel("Region:"))
        for label, color in [("Arm", JB_ARM_COLOR), ("PeriCEN", JB_PERICEN_COLOR), ("CEN", JB_CEN_COLOR)]:
            swatch = QLabel("■")
            swatch.setStyleSheet(f"color: {color}; font-size: 14px;")
            legend_layout.addWidget(swatch)
            legend_layout.addWidget(QLabel(label))
        legend_layout.addStretch()
        legend_layout.addWidget(QLabel("← Drag/scroll to navigate  |  Click feature for detail  |  Dashed = CEN BED region"))
        layout.addWidget(legend_frame)

        # ── Detail panel ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.canvas)

        panel = QFrame()
        panel.setMaximumWidth(380)
        panel.setStyleSheet(f"QFrame {{ background: {JB_BG}; border-left: 1px solid {JB_TRACK_BORDER}; }}")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(12, 8, 12, 8)

        pl.addWidget(QLabel("LTR Detail"))
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("monospace", 9))
        self.detail.setStyleSheet(f"border: 1px solid {JB_TRACK_BORDER}; border-radius: 4px; padding: 8px;")
        pl.addWidget(self.detail)

        pl.addWidget(QLabel("Superfamily Legend"))
        legend = QTextEdit()
        legend.setReadOnly(True)
        legend.setFont(QFont("monospace", 9))
        legend.setMaximumHeight(260)
        legend.setStyleSheet(f"border: 1px solid {JB_TRACK_BORDER}; border-radius: 4px; padding: 6px;")
        lines = []
        for sf, color in sorted(SUPERFAMILY_COLORS.items()):
            lines.append(f'<span style="color:{color};">●</span> {sf}')
        legend.setHtml("<br>".join(lines))
        pl.addWidget(legend)

        splitter.addWidget(panel)
        splitter.setSizes([950, 350])
        layout.addWidget(splitter)

    # ── Public ──────────────────────────────────────────────────────────────

    def set_species(self, species: str):
        if species == self._species: return
        self._species = species
        self.species_lbl.setText(species)
        self._chrs = get_chromosomes(species)
        self._cache.clear()
        self._build_chr_bar()
        self.chr_combo.blockSignals(True)
        self.chr_combo.clear(); self.chr_combo.addItems(self._chrs)
        self.chr_combo.blockSignals(False)
        if self._chrs:
            self._on_chr_changed(self._chrs[0])

    def jump_to_location(self, chr_name: str, pos: int):
        if chr_name not in self._cache:
            self._cache[chr_name] = get_ltrs_for_chromosome(self._species, chr_name)
        self._select_chr(chr_name)
        self.canvas.load(self._species, chr_name, self._cache[chr_name])
        self.canvas.jump_to(pos)
        self._update_range()

    # ── Internal ────────────────────────────────────────────────────────────

    def _build_chr_bar(self):
        while self.chr_bar.count():
            w = self.chr_bar.takeAt(0).widget()
            if w: w.deleteLater()
        for name in self._chrs[:30]:
            btn = QPushButton(name)
            btn.setFixedSize(46, 20)
            btn.setFont(QFont("", 7))
            btn.setStyleSheet("""
                QPushButton {
                    background: #E8EAF6; border: 1px solid #C5CAE9; border-radius: 2px;
                    padding: 1px 3px; color: #283593;
                }
                QPushButton:hover { background: #C5CAE9; border-color: #7986CB; }
            """)
            btn.clicked.connect(lambda _, c=name: self._select_chr(c))
            self.chr_bar.addWidget(btn)
        self.chr_bar.addStretch()

    def _select_chr(self, name):
        idx = self.chr_combo.findText(name)
        if idx >= 0: self.chr_combo.setCurrentIndex(idx)

    def _on_chr_changed(self, name):
        if not name: return
        self._current_chr = name
        if name not in self._cache:
            self._cache[name] = get_ltrs_for_chromosome(self._species, name)
        self.canvas.load(self._species, name, self._cache[name])
        self._update_range()

    def _on_feature_click(self, ltr: dict):
        """Show detailed SoloLTR information in the right panel."""
        length = ltr.get("end", 0) - ltr.get("start", 0)
        rc = ltr.get("region_code", 0)
        rc_name = {0: "Arm", 1: "PeriCEN", 2: "CEN"}.get(rc, "?")
        sf = ltr.get("superfamily", "?")
        sf_color = SUPERFAMILY_COLORS.get(sf, DEFAULT_SF_COLOR)

        # SoloLTR title badge
        region_colors = {"Arm": JB_ARM_COLOR, "Pericentromere": JB_PERICEN_COLOR, "Centromere": JB_CEN_COLOR}
        rc_color = region_colors.get(ltr.get("region", ""), JB_ARM_COLOR)

        html = (
            f'<div style="margin-bottom:8px;">'
            f'<span style="background:{rc_color};color:white;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:bold;">'
            f'SoloLTR · {rc_name}</span>'
            f'</div>'
            f'<b style="font-size:11px;">{ltr.get("solo_id", "N/A")}</b><br><br>'
            f'<table style="font-size:10px;border-collapse:collapse;">'
            f'<tr><td style="color:#757575;padding-right:12px;">Position</td>'
            f'<td>{ltr.get("chr","")}:{ltr.get("start",0):,}–{ltr.get("end",0):,}</td></tr>'
            f'<tr><td style="color:#757575;">Length</td><td>{length:,} bp</td></tr>'
            f'<tr><td style="color:#757575;">Superfamily</td>'
            f'<td><b style="color:{sf_color};">{sf}</b></td></tr>'
            f'<tr><td style="color:#757575;">Region</td><td>{ltr.get("region","?")}</td></tr>'
            f'<tr><td style="color:#757575;">Confidence</td><td>{ltr.get("confidence","?")}</td></tr>'
            f'</table><br>'
            f'<b style="font-size:10px;">Alignment</b><br>'
            f'<table style="font-size:10px;border-collapse:collapse;">'
            f'<tr><td style="color:#757575;padding-right:12px;">Identity</td>'
            f'<td>{ltr.get("pident",0):.1f}%</td></tr>'
            f'<tr><td style="color:#757575;">Aln Length</td><td>{ltr.get("aln_length",0):,} bp</td></tr>'
            f'<tr><td style="color:#757575;">Mismatch</td><td>{ltr.get("mismatch",0)}</td></tr>'
            f'<tr><td style="color:#757575;">Gap</td><td>{ltr.get("gap",0)}</td></tr>'
            f'<tr><td style="color:#757575;">E-value</td><td>{ltr.get("evalue",0):.2e}</td></tr>'
            f'<tr><td style="color:#757575;">Bitscore</td><td>{ltr.get("bitscore",0):.1f}</td></tr>'
            f'</table><br>'
            f'<b style="font-size:10px;">Reference LTR</b><br>'
            f'<table style="font-size:10px;border-collapse:collapse;">'
            f'<tr><td style="color:#757575;padding-right:12px;">Ref LTR</td>'
            f'<td style="font-size:9px;">{ltr.get("ref_ltr","?")[:80]}</td></tr>'
            f'<tr><td style="color:#757575;">Target ID</td>'
            f'<td style="font-size:9px;">{ltr.get("target_ltr_id","?")[:80]}</td></tr>'
            f'</table>'
        )
        self.detail.setHtml(html)

    def _update_range(self):
        v0, v1 = self.canvas.view_range()
        self.range_lbl.setText(f"{v0:,} – {v1:,}  ({v1 - v0:,} bp)")
