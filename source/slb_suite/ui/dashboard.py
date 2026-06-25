"""Dashboard widget: species overview and quick navigation."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QGridLayout, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush

from slb_suite.db.loader import get_stats, get_genome_info, get_all_genome_info, get_all_stats

# ── Color palette ────────────────────────────────────────────────────────────
C_PRIMARY    = "#1565C0"  # deep blue
C_ACCENT     = "#0D47A1"  # darker blue
C_SUCCESS    = "#2E7D32"  # green
C_WARN       = "#E65100"  # orange
C_DANGER     = "#C62828"  # red
C_TEXT       = "#212121"
C_TEXT_MUTED = "#616161"
C_BG         = "#FAFAFA"
C_SURFACE    = "#FFFFFF"
C_BORDER     = "#E0E0E0"
C_CHIP_BG    = "#E3F2FD"
C_ROW_ALT    = "#F5F5F5"


class DashboardWidget(QWidget):
    species_selected = pyqtSignal(str)
    navigate_genome_browser = pyqtSignal()
    navigate_blast = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._species_list: list[str] = []
        self._genome_info: dict[str, dict] = {}
        self._stats_list: list[dict] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ── Header ──
        header = QHBoxLayout()
        title = QLabel("LTRtrace-Search")
        title.setFont(self._font(22, True))
        title.setStyleSheet(f"color: {C_PRIMARY};")
        subtitle = QLabel("— Dashboard")
        subtitle.setFont(self._font(16, False))
        subtitle.setStyleSheet(f"color: {C_TEXT_MUTED};")
        header.addStretch()
        header.addWidget(title)
        header.addWidget(subtitle)
        header.addStretch()
        layout.addLayout(header)

        # ── Introduction ──
        intro = QLabel(
            "A cross-species SoloLTR transposable element database "
            "integrating annotation data from 18 legume species "
            "into a unified, interactive desktop application."
        )
        intro.setFont(self._font(10))
        intro.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 2px 40px;")
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # ── Species selector ──
        sel_row = QHBoxLayout()
        sel_row.setSpacing(10)
        lbl = QLabel("Select Species:")
        lbl.setFont(self._font(12))
        lbl.setStyleSheet(f"color: {C_TEXT};")
        self.species_combo = QComboBox()
        self.species_combo.setMinimumWidth(380)
        self.species_combo.setFont(self._font(12))
        self.species_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 14px; border: 2px solid {C_BORDER};
                border-radius: 8px; background: {C_SURFACE};
                font-size: 13px; color: {C_TEXT};
            }}
            QComboBox:hover {{ border-color: {C_PRIMARY}; }}
            QComboBox:focus {{ border-color: {C_PRIMARY}; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox QAbstractItemView {{
                border: 1px solid {C_BORDER}; border-radius: 4px;
                padding: 4px; background: {C_SURFACE};
                font-size: 12px;
            }}
        """)
        self.species_combo.currentIndexChanged.connect(self._on_species_index_changed)
        sel_row.addStretch()
        sel_row.addWidget(lbl)
        sel_row.addWidget(self.species_combo)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        # ── Top row: LTR Stats (compact) + Genome Info (expanded) ──
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # -- SoloLTR Stats (narrow) --
        stats_card = self._make_card("SoloLTR Annotation Data")
        stats_content = stats_card._content_widget
        stats_grid = QGridLayout(stats_content)
        stats_grid.setSpacing(10)
        stats_grid.setContentsMargins(16, 8, 16, 12)

        self.stat_labels = {}
        pairs = [
            ("Total SoloLTRs", "total_ltr"),
            ("CEN SoloLTRs", "cen_ltr"),
            ("PeriCEN SoloLTRs", "pericen_ltr"),
            ("Arm SoloLTRs", "arm_ltr"),
        ]
        for i, (display, key) in enumerate(pairs):
            num = QLabel("0")
            num.setFont(self._font(22, True))
            num.setStyleSheet(f"color: {C_PRIMARY};")
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(display)
            lbl.setFont(self._font(10))
            lbl.setStyleSheet(f"color: {C_TEXT_MUTED};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row, col = divmod(i, 2)
            stats_grid.addWidget(num, row * 2, col, Qt.AlignmentFlag.AlignCenter)
            stats_grid.addWidget(lbl, row * 2 + 1, col, Qt.AlignmentFlag.AlignCenter)
            self.stat_labels[key] = num

        top_row.addWidget(stats_card, 1)

        # -- Genome Info (wide) --
        info_card = self._make_card("Genome Information")
        info_content = info_card._content_widget
        info_grid = QGridLayout(info_content)
        info_grid.setSpacing(8)
        info_grid.setContentsMargins(16, 8, 16, 12)

        self.info_labels: dict[str, QLabel] = {}
        fields = [
            ("latin", "Latin Name"),
            ("assembly", "Assembly Size"),
            ("scaffolds", "Scaffolds"),
            ("n50_s", "Scaffold N50"),
            ("n50_c", "Contig N50"),
            ("gc", "GC Content"),
            ("busco", "BUSCO"),
            ("gaps", "Total Gaps"),
            ("gapped_cen", "Gapped CEN"),
            ("source_file", "Reference"),
        ]
        for i, (key, display) in enumerate(fields):
            kv = QLabel(display)
            kv.setFont(self._font(10))
            kv.setStyleSheet(f"color: {C_TEXT_MUTED};")
            kv.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            vv = QLabel("-")
            vv.setFont(self._font(10, True))
            vv.setStyleSheet(f"color: {C_TEXT};")
            vv.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row, col = divmod(i, 2)
            info_grid.addWidget(kv, row, col * 2)
            info_grid.addWidget(vv, row, col * 2 + 1)
            self.info_labels[key] = vv

        top_row.addWidget(info_card, 2)
        layout.addLayout(top_row)

        # ── Quick nav buttons ──
        nav_row = QHBoxLayout()
        nav_row.setSpacing(14)
        for text, slot, icon_color in [
            ("Genome Browser", self.navigate_genome_browser.emit, "#1565C0"),
            ("BLAST Search", self.navigate_blast.emit, "#2E7D32"),
            ("Analysis", None, "#E65100"),
        ]:
            btn = QPushButton(text)
            btn.setMinimumHeight(44)
            btn.setFont(self._font(12, True))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C_SURFACE}; color: {icon_color};
                    border: 2px solid {icon_color}; border-radius: 8px;
                    padding: 8px 24px;
                }}
                QPushButton:hover {{
                    background: {icon_color}; color: white;
                }}
                QPushButton:pressed {{
                    background: {icon_color}; color: white;
                }}
            """)
            if slot:
                btn.clicked.connect(slot)
            nav_row.addWidget(btn)
        nav_row.addStretch()
        layout.addLayout(nav_row)

        # ── Species overview table ──
        table_card = self._make_card("Species Overview")
        table_content = table_card._content_widget
        table_layout = QVBoxLayout(table_content)
        table_layout.setContentsMargins(8, 4, 8, 8)

        self.species_table = QTableWidget(0, 8)
        self.species_table.setHorizontalHeaderLabels([
            "Species", "Latin Name", "Assembly (Mb)", "SoloLTRs",
            "CEN %", "BUSCO %", "Gaps", "Reference",
        ])
        self.species_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.species_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.species_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.species_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.species_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.species_table.setAlternatingRowColors(True)
        self.species_table.verticalHeader().setVisible(False)
        self.species_table.setSortingEnabled(True)
        self.species_table.verticalHeader().setDefaultSectionSize(28)
        self.species_table.setFont(self._font(10))
        self.species_table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {C_BORDER};
                background: {C_SURFACE};
                border: none;
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget::item:selected {{
                background: {C_CHIP_BG};
                color: {C_TEXT};
            }}
            QHeaderView::section {{
                background: {C_BG};
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid {C_PRIMARY};
                font-weight: bold;
                font-size: 10px;
                color: {C_PRIMARY};
            }}
        """)
        self.species_table.cellClicked.connect(self._on_table_row_clicked)
        table_layout.addWidget(self.species_table)
        layout.addWidget(table_card, 1)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _font(self, size: int, bold: bool = False) -> QFont:
        w = QFont.Weight.Bold if bold else QFont.Weight.Normal
        f = QFont()
        f.setPointSize(size)
        f.setWeight(w)
        return f

    def _make_card(self, title: str) -> QFrame:
        """Create a styled card frame with a title label."""
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {C_SURFACE}; border: 1px solid {C_BORDER}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_lbl = QLabel(title)
        title_lbl.setFont(self._font(11, True))
        title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {C_PRIMARY};
                padding: 10px 16px 6px 16px;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(title_lbl)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {C_BORDER}; max-height: 1px; margin: 0 12px;")
        layout.addWidget(sep)

        # Content area wrapped in a container
        content = QWidget()
        self._card_content_layout = None  # placeholder, set per-card below
        card._content_widget = content
        card._card_layout = layout
        layout.addWidget(content)
        return card

    # ── Public API ────────────────────────────────────────────────────────────

    def set_species_list(self, species_list: list[str]):
        self._species_list = species_list
        self._genome_info = get_all_genome_info()
        self._stats_list = get_all_stats()

        # Populate combo box
        self.species_combo.blockSignals(True)
        self.species_combo.clear()
        for sp in species_list:
            info = self._genome_info.get(sp, {})
            latin = info.get("latin_name", "")
            display = f"{sp}  —  {latin}" if latin else sp
            self.species_combo.addItem(display, sp)
        if species_list:
            self.species_combo.setCurrentIndex(0)
            self._update_display(species_list[0])
            self.species_selected.emit(species_list[0])
        self.species_combo.blockSignals(False)

        # Populate species table
        self._populate_species_table()

    def _on_species_index_changed(self, idx: int):
        if idx < 0:
            return
        sp = self.species_combo.itemData(idx)
        if sp:
            self._update_display(sp)
            self.species_selected.emit(sp)
            # Highlight row in table
            for r in range(self.species_table.rowCount()):
                item = self.species_table.item(r, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == sp:
                    self.species_table.selectRow(r)
                    break

    def _on_table_row_clicked(self, row: int, col: int):
        item = self.species_table.item(row, 0)
        if item:
            sp = item.data(Qt.ItemDataRole.UserRole)
            if sp:
                idx = self.species_combo.findData(sp)
                if idx >= 0:
                    self.species_combo.setCurrentIndex(idx)

    # ── Update ────────────────────────────────────────────────────────────────

    def _update_display(self, species: str):
        if not species:
            return
        stats = get_stats(species)
        for key in ("total_ltr", "cen_ltr", "pericen_ltr", "arm_ltr"):
            self.stat_labels[key].setText(f"{stats.get(key, 0):,}")

        info = self._genome_info.get(species, {})
        total = stats.get("total_ltr", 0)
        cen = stats.get("cen_ltr", 0)

        self.info_labels["latin"].setText(
            f"<i>{info.get('latin_name', '-')}</i>")
        asm = info.get("assembly_size", 0)
        self.info_labels["assembly"].setText(
            f"{asm:,.1f} Mb" if asm else "-")
        self.info_labels["scaffolds"].setText(
            str(info.get("scaffold_number", "-")))
        self.info_labels["n50_s"].setText(
            f"{info.get('scaffold_n50', 0):,.1f} Mb" if info.get("scaffold_n50") else "-")
        self.info_labels["n50_c"].setText(
            f"{info.get('contig_n50', 0):,.1f} Mb" if info.get("contig_n50") else "-")
        gc = info.get("gc_content", 0)
        self.info_labels["gc"].setText(f"{gc:.1f}%" if gc else "-")
        busco = info.get("busco", 0)
        self.info_labels["busco"].setText(
            f'<span style="color:{C_SUCCESS if busco>=99 else C_WARN};">{busco:.1f}%</span>'
            if busco else "-")
        gaps = info.get("gap_number", 0)
        gcen = info.get("gapped_centromere", 0)
        self.info_labels["gaps"].setText(f"{gaps:,}" if gaps else "0")
        self.info_labels["gapped_cen"].setText(f"{gcen:,}" if gcen else "0")
        ref = info.get("source_title", "") or info.get("source_file", "")
        if not ref and info.get("source", "") == "This study":
            ref = "This Study"
        self.info_labels["source_file"].setText(
            f'<span style="font-size:9px;">{ref}</span>' if ref else "-")

    def _populate_species_table(self):
        stats_map = {s["species"]: s for s in self._stats_list}
        all_species = sorted(set(
            list(self._genome_info.keys()) + list(stats_map.keys())
        ))
        self.species_table.setRowCount(len(all_species))
        self.species_table.setSortingEnabled(False)

        for i, sp in enumerate(all_species):
            info = self._genome_info.get(sp, {})
            st = stats_map.get(sp, {})

            # Species code
            sp_item = QTableWidgetItem(sp)
            sp_item.setData(Qt.ItemDataRole.UserRole, sp)
            sp_item.setFont(self._font(10, True))
            self.species_table.setItem(i, 0, sp_item)

            # Latin name
            latin = info.get("latin_name", "-")
            self.species_table.setItem(i, 1, QTableWidgetItem(latin))

            # Assembly size
            asm = info.get("assembly_size", 0)
            asm_item = QTableWidgetItem(f"{asm:,.0f}" if asm else "-")
            asm_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.species_table.setItem(i, 2, asm_item)

            # LTRs
            total_ltr = st.get("total_ltr", 0)
            ltr_item = QTableWidgetItem(f"{total_ltr:,}" if total_ltr else "-")
            ltr_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.species_table.setItem(i, 3, ltr_item)

            # CEN %
            total = st.get("total_ltr", 0)
            cen = st.get("cen_ltr", 0)
            cen_pct = f"{cen / total * 100:.1f}" if total > 0 else "-"
            cen_item = QTableWidgetItem(cen_pct)
            cen_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.species_table.setItem(i, 4, cen_item)

            # BUSCO
            busco = info.get("busco", 0)
            busco_item = QTableWidgetItem(f"{busco:.1f}" if busco else "-")
            busco_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if busco >= 99:
                busco_item.setForeground(QBrush(QColor(C_SUCCESS)))
            elif busco > 0:
                busco_item.setForeground(QBrush(QColor(C_WARN)))
            self.species_table.setItem(i, 5, busco_item)

            # Gaps
            gaps = info.get("gap_number", -1)
            gaps_item = QTableWidgetItem(f"{gaps:,}" if gaps >= 0 else "-")
            gaps_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.species_table.setItem(i, 6, gaps_item)

            # Reference
            ref = info.get("source_title", "") or info.get("source_file", "")
            if not ref and info.get("source", "") == "This study":
                ref = "This Study"
            ref_item = QTableWidgetItem(ref if ref else "-")
            ref_item.setToolTip(ref if ref else "")
            self.species_table.setItem(i, 7, ref_item)

        self.species_table.setSortingEnabled(True)
