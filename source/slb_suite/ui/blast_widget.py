"""BLAST Search widget with SoloLTR/Complete_LTR type annotation."""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QDoubleSpinBox, QSpinBox, QHeaderView,
    QMessageBox, QProgressBar, QSplitter, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QBrush

from slb_suite.blast.engine import run_blast, get_sequence_for_hit


class BlastWorker(QThread):
    finished = pyqtSignal(bool, object)
    progress = pyqtSignal(str)

    def __init__(self, species: str, query: str, evalue: float, max_hits: int):
        super().__init__()
        self.species = species
        self.query = query
        self.evalue = evalue
        self.max_hits = max_hits

    def run(self):
        self.progress.emit("Building combined BLAST database (NR library + SoloLTR)...")
        ok, result = run_blast(self.species, self.query, self.evalue, self.max_hits)
        self.finished.emit(ok, result)


class BlastWidget(QWidget):
    navigate_to_locus = pyqtSignal(str, str, int)  # species, chr, pos

    COLUMNS = [
        "Query", "Type", "Hit ID", "Identity %", "E-value",
        "Bitscore", "Genomic Chr", "Location", "Region", "Download",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._species: str = ""
        self._results: list[dict] = []
        self._worker: BlastWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Query input ──
        input_group = QGroupBox("Query Sequence")
        input_layout = QVBoxLayout(input_group)

        hint = QLabel("Paste DNA sequence (FASTA or raw sequence):")
        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText(
            ">query\nATGCGTACGTAGCTAGCTAGCATCGATCGA..."
        )
        self.query_input.setMaximumHeight(120)
        self.query_input.setFont(QFont("monospace", 10))
        input_layout.addWidget(hint)
        input_layout.addWidget(self.query_input)
        layout.addWidget(input_group)

        # ── Parameters ──
        param_layout = QHBoxLayout()
        param_layout.setSpacing(12)

        param_layout.addWidget(QLabel("Database Species:"))
        self.species_label = QLabel("(select species first)")
        self.species_label.setFont(QFont("", 10, QFont.Weight.Bold))
        param_layout.addWidget(self.species_label)
        param_layout.addSpacing(20)

        param_layout.addWidget(QLabel("E-value:"))
        self.evalue_spin = QDoubleSpinBox()
        self.evalue_spin.setDecimals(10)
        self.evalue_spin.setValue(1e-5)
        self.evalue_spin.setSingleStep(1e-5)
        self.evalue_spin.setToolTip("E-value cutoff for BLAST results")
        param_layout.addWidget(self.evalue_spin)
        param_layout.addSpacing(15)

        param_layout.addWidget(QLabel("Max hits:"))
        self.maxhits_spin = QSpinBox()
        self.maxhits_spin.setRange(1, 1000)
        self.maxhits_spin.setValue(100)
        param_layout.addWidget(self.maxhits_spin)
        param_layout.addStretch()

        self.btn_search = QPushButton("Run BLAST")
        self.btn_search.setMinimumHeight(34)
        self.btn_search.setFont(QFont("", 11, QFont.Weight.Bold))
        self.btn_search.clicked.connect(self._run_blast)
        param_layout.addWidget(self.btn_search)
        layout.addLayout(param_layout)

        # ── Progress ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ── Results table ──
        results_group = QGroupBox("BLAST Results")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget(0, len(self.COLUMNS))
        self.results_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        # Download column: fixed width
        self.results_table.horizontalHeader().setSectionResizeMode(
            len(self.COLUMNS) - 1, QHeaderView.ResizeMode.Fixed
        )
        self.results_table.setColumnWidth(len(self.COLUMNS) - 1, 80)
        self.results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.cellDoubleClicked.connect(self._on_result_double_clicked)
        results_layout.addWidget(self.results_table)

        self.status_label = QLabel("Ready — results include both Complete_LTR and SoloLTR hits")
        self.status_label.setFont(QFont("", 9))
        results_layout.addWidget(self.status_label)
        layout.addWidget(results_group)

    def set_species(self, species: str):
        self._species = species
        if species:
            self.species_label.setText(species)

    def _run_blast(self):
        if not self._species:
            QMessageBox.warning(self, "No Species", "Please select a species first.")
            return
        query = self.query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "No Query", "Please enter a query sequence.")
            return

        self.btn_search.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.results_table.setRowCount(0)
        self._results = []

        self._worker = BlastWorker(
            self._species, query,
            self.evalue_spin.value(),
            self.maxhits_spin.value(),
        )
        self._worker.progress.connect(
            lambda msg: self.status_label.setText(msg)
        )
        self._worker.finished.connect(self._on_blast_finished)
        self._worker.start()

    def _on_blast_finished(self, ok: bool, result):
        self.btn_search.setEnabled(True)
        self.progress_bar.setVisible(False)

        if not ok:
            QMessageBox.critical(self, "BLAST Error", str(result))
            self.status_label.setText("BLAST failed")
            return

        self._results = result

        # Count types
        n_solo = sum(1 for h in result if h.get("ltr_type") == "SoloLTR")
        n_complete = sum(1 for h in result if h.get("ltr_type") == "Complete_LTR")

        self.results_table.setRowCount(len(result))
        for i, hit in enumerate(result):
            self.results_table.setItem(
                i, 0, QTableWidgetItem(hit.get("qseqid", "")))

            # Type column with color
            ltr_type = hit.get("ltr_type", "Unknown")
            type_item = QTableWidgetItem(ltr_type)
            if ltr_type == "SoloLTR":
                type_item.setBackground(QBrush(QColor("#E8F5E9")))
                type_item.setForeground(QBrush(QColor("#2E7D32")))
                type_item.setFont(QFont("", 9, QFont.Weight.Bold))
            elif ltr_type == "Complete_LTR":
                type_item.setBackground(QBrush(QColor("#E3F2FD")))
                type_item.setForeground(QBrush(QColor("#1565C0")))
                type_item.setFont(QFont("", 9, QFont.Weight.Bold))
            self.results_table.setItem(i, 1, type_item)

            # Hit ID
            self.results_table.setItem(
                i, 2, QTableWidgetItem(hit.get("sseqid", "")))

            # Identity
            self.results_table.setItem(
                i, 3, QTableWidgetItem(f"{hit.get('pident', 0):.1f}"))

            # E-value
            self.results_table.setItem(
                i, 4, QTableWidgetItem(f"{hit.get('evalue', 0):.2e}"))

            # Bitscore
            self.results_table.setItem(
                i, 5, QTableWidgetItem(f"{hit.get('bitscore', 0):.1f}"))

            # Genomic location
            chr_name = hit.get("genomic_chr", hit.get("solo_chr", "N/A"))
            start = hit.get("genomic_start", hit.get("solo_start", 0))
            end = hit.get("genomic_end", hit.get("solo_end", 0))
            self.results_table.setItem(i, 6, QTableWidgetItem(str(chr_name)))

            if start > 0:
                loc_str = f"{start:,} – {end:,}"
            else:
                loc_str = "N/A"
            self.results_table.setItem(i, 7, QTableWidgetItem(loc_str))

            region = hit.get("genomic_region", hit.get("solo_region", "N/A"))
            self.results_table.setItem(i, 8, QTableWidgetItem(region))

            # Download button
            btn_dl = QPushButton("⬇ FASTA")
            btn_dl.setFixedSize(72, 24)
            btn_dl.setFont(QFont("", 7, QFont.Weight.Bold))
            btn_dl.setStyleSheet("""
                QPushButton {
                    background: #E8F5E9; color: #2E7D32;
                    border: 1px solid #A5D6A7; border-radius: 3px;
                    padding: 1px 4px;
                }
                QPushButton:hover {
                    background: #C8E6C9; border-color: #66BB6A;
                }
                QPushButton:pressed {
                    background: #A5D6A7;
                }
            """)
            btn_dl.clicked.connect(lambda checked, r=i: self._download_sequence(r))
            self.results_table.setCellWidget(i, len(self.COLUMNS) - 1, btn_dl)

        self.status_label.setText(
            f"Found {len(result)} hits — "
            f"<span style='color:#2E7D32;'><b>{n_solo} SoloLTR</b></span> · "
            f"<span style='color:#1565C0;'>{n_complete} Complete_LTR</span>"
        )

    def _on_result_double_clicked(self, row: int, col: int):
        if row < 0 or row >= len(self._results):
            return
        hit = self._results[row]
        chr_name = hit.get("genomic_chr", hit.get("solo_chr", ""))
        if not chr_name or chr_name == "N/A":
            return
        pos = hit.get("genomic_start", hit.get("solo_start", 0))
        if pos <= 0:
            return
        # Normalize chr name (some species use Chr1 vs chr1)
        if chr_name.startswith("Chr") and chr_name[0].isupper():
            chr_name = "c" + chr_name[1:]
        self.navigate_to_locus.emit(self._species, chr_name, pos)

    def _download_sequence(self, row: int):
        """Download the FASTA sequence for a BLAST hit."""
        if row < 0 or row >= len(self._results):
            return
        hit = self._results[row]
        sseqid_tagged = hit.get("sseqid_tagged", "")
        ltr_type = hit.get("ltr_type", "Unknown")
        sseqid = hit.get("sseqid", "unknown")

        if not sseqid_tagged:
            QMessageBox.warning(self, "Download Failed", "No sequence ID found for this hit.")
            return

        header, seq = get_sequence_for_hit(self._species, sseqid_tagged)
        if not seq:
            QMessageBox.warning(self, "Download Failed",
                              f"Could not retrieve sequence for:\n{sseqid}")
            return

        # Suggest filename
        safe_id = sseqid.replace("/", "_").replace("|", "_")[:60]
        default_name = f"{self._species}_{ltr_type}_{safe_id}.fasta"

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Sequence", default_name,
            "FASTA Files (*.fasta *.fa);;All Files (*)",
        )
        if not path:
            return

        try:
            with open(path, "w") as f:
                f.write(f">{header}\n")
                for i in range(0, len(seq), 60):
                    f.write(seq[i:i + 60] + "\n")
            self.status_label.setText(
                f"Sequence saved: {os.path.basename(path)} ({len(seq):,} bp)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))
