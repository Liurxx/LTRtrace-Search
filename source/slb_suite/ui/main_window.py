"""Main application window with tab navigation."""

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QMenuBar, QMenu,
    QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from slb_suite.ui.dashboard import DashboardWidget
from slb_suite.ui.genome_browser import GenomeBrowserWidget
from slb_suite.ui.blast_widget import BlastWidget
from slb_suite.ui.analysis_widget import AnalysisWidget
from slb_suite.db.loader import database_is_built, get_species_list
from slb_suite import __version__


class MainWindow(QMainWindow):
    species_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"LTRtrace-Search v{__version__}")
        self.resize(1400, 900)
        self._db_ready: bool = False
        self._current_species: str = ""
        self._species_list: list[str] = []

        self._setup_menu()
        self._setup_ui()
        self._check_database()

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        refresh_action = QAction("&Refresh Database", self)
        refresh_action.triggered.connect(self._check_database)
        file_menu.addAction(refresh_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.dashboard = DashboardWidget()
        self.genome_browser = GenomeBrowserWidget()
        self.blast_widget = BlastWidget()
        self.analysis_widget = AnalysisWidget()

        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.genome_browser, "Genome Browser")
        self.tabs.addTab(self.blast_widget, "BLAST Search")
        self.tabs.addTab(self.analysis_widget, "Analysis")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Wire signals
        self.dashboard.species_selected.connect(self._on_species_changed)
        self.dashboard.navigate_genome_browser.connect(self._navigate_genome_browser)
        self.dashboard.navigate_blast.connect(self._navigate_blast)

    def _check_database(self):
        if database_is_built():
            self._db_ready = True
            self._species_list = get_species_list()
            self.dashboard.set_species_list(self._species_list)
            self.status_bar.showMessage(
                f"Database ready — {len(self._species_list)} species loaded"
            )
        else:
            self._db_ready = False
            self._species_list = []
            self.status_bar.showMessage("Database not built. Run data loader first.")
            QMessageBox.information(
                self, "Database Required",
                "No database found. Please run the data loader to initialize the database.\n\n"
                "python -m slb_suite.db.loader",
            )

    def _on_species_changed(self, species: str):
        self._current_species = species
        self.genome_browser.set_species(species)
        self.blast_widget.set_species(species)
        self.analysis_widget.set_species(species)

    def _navigate_genome_browser(self):
        self.tabs.setCurrentWidget(self.genome_browser)

    def _navigate_blast(self):
        self.tabs.setCurrentWidget(self.blast_widget)

    def navigate_to_genome_location(self, species: str, chr_name: str, pos: int):
        """Navigate genome browser to a specific location."""
        self._on_species_changed(species)
        self.genome_browser.jump_to_location(chr_name, pos)
        self.tabs.setCurrentWidget(self.genome_browser)

    def _show_about(self):
        QMessageBox.about(
            self, "About LTRtrace-Search",
            f"<h3>LTRtrace-Search v{__version__}</h3>"
            "<p>A cross-species SoloLTR transposable element database "
            "integrating annotation data from 18 legume species "
            "into a unified, interactive desktop application "
            "with BLAST search and genome browsing capabilities.</p>"
            "<p>Built with PyQt6 | Data stored in SQLite</p>",
        )
