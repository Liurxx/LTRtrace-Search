"""Global configuration and path resolution for CenSoloLTR-Search."""

import os
import sys


def _is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, 'frozen', False)


def _get_app_dir() -> str:
    """Application root directory (contains the executable).

    - PyInstaller --onefile:  directory of sys.executable
    - PyInstaller --onedir:   directory of sys.executable
    - macOS .app bundle:      Contents/  (parent of MacOS/)
    - dev mode:               SLB_Suite/  (project root)
    """
    if _is_frozen():
        exe_dir = os.path.dirname(sys.executable)
        # macOS .app:  Contents/MacOS/ -> Contents/
        if sys.platform == 'darwin' and os.path.basename(exe_dir) == 'MacOS':
            return os.path.dirname(exe_dir)
        return exe_dir
    # Dev mode:  slb_suite/utils/config.py  ->  SLB_Suite/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _get_data_root() -> str:
    """Data root directory (contains ltr.sqlite and annotation data folders).

    Resolution order:
    1. Environment variable CENSOLOLTR_DATA_DIR
    2. Packaged mode:  <app_dir>/data/
    3. Dev mode:        <SLB_Suite>/../  (the database root directory)
    4. Fallback:        <app_dir>/
    """
    env = os.environ.get('CENSOLOLTR_DATA_DIR', '')
    if env and os.path.isdir(env):
        return env

    app_dir = _get_app_dir()

    # Packaged mode — data/ lives next to or inside the bundle
    for candidate in [
        os.path.join(app_dir, 'data'),
        os.path.join(app_dir, '..', 'data'),
    ]:
        if os.path.isdir(candidate):
            return candidate

    # Dev mode — data lives one level above SLB_Suite/
    dev_root = os.path.dirname(app_dir)
    if os.path.isfile(os.path.join(dev_root, 'SLB_Suite', 'ltr.sqlite')):
        return dev_root

    return app_dir


# ── Resolved paths ──────────────────────────────────────────────────────────
APP_DIR    = _get_app_dir()       # SLB_Suite/  (dev) or exe-dir/ (packaged)
DATA_ROOT  = _get_data_root()     # parent of SLB_Suite/ (dev) or data/ (packaged)

# Data directories (under DATA_ROOT in dev mode)
LTR_LIB_DIR    = os.path.join(DATA_ROOT, '0.NonRedundant_LTR_Libraries')
GENOME_INDEX_DIR = os.path.join(DATA_ROOT, '0.genome_data_index')
CEN_TSV_DIR    = os.path.join(DATA_ROOT, '10.CEN_PeriCEN_Final_Annotations_1')
CEN_FASTA_DIR  = os.path.join(DATA_ROOT, '11.CEN_PeriCEN_SoloLTR_FASTA_1')
ARM_TSV_DIR    = os.path.join(DATA_ROOT, '12.Arm_Final_Annotations_1')
ARM_FASTA_DIR  = os.path.join(DATA_ROOT, '13.Arm_SoloLTR_FASTA_1')
CEN_BED_DIR    = os.path.join(DATA_ROOT, '2.CEN_region_Bed')
GENOME_INFO_FILE = os.path.join(DATA_ROOT, '0.1.genome_information', 'genome_information.txt')
SOURCE_DIR     = os.path.join(DATA_ROOT, '0.1.genome_information', 'Source')

# Database paths — check data/ subdirectory first (packaged), then project root (dev)
if os.path.isfile(os.path.join(DATA_ROOT, 'ltr.sqlite')):
    LTR_DB_PATH  = os.path.join(DATA_ROOT, 'ltr.sqlite')
    ANNO_DB_PATH = os.path.join(DATA_ROOT, 'annotation.sqlite')
else:
    LTR_DB_PATH  = os.path.join(DATA_ROOT, 'SLB_Suite', 'ltr.sqlite')
    ANNO_DB_PATH = os.path.join(DATA_ROOT, 'SLB_Suite', 'annotation.sqlite')

# BLAST databases directory — user-writable location
if sys.platform == 'darwin':
    BLAST_DB_DIR = os.path.join(
        os.path.expanduser('~/Library/Application Support'),
        'CenSoloLTR-Search', 'blast_dbs',
    )
elif sys.platform == 'win32':
    BLAST_DB_DIR = os.path.join(
        os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
        'CenSoloLTR-Search', 'blast_dbs',
    )
elif _is_frozen():
    # Linux packaged mode (AppImage): use user cache (AppImage mount is read-only)
    BLAST_DB_DIR = os.path.join(
        os.path.expanduser('~/.cache'), 'CenSoloLTR-Search', 'blast_dbs',
    )
else:
    BLAST_DB_DIR = os.path.join(APP_DIR, 'blast_dbs')


def ensure_blast_db_dir() -> str:
    """Create and return the BLAST database directory."""
    os.makedirs(BLAST_DB_DIR, exist_ok=True)
    return BLAST_DB_DIR


# Species mapping: TSV species name -> LTR library directory name
SPECIES_LIB_MAP = {
    'Cari': 'Cari', 'Cchi': 'Cchi', 'Dreg': 'Dreg',
    'Glygla': 'Glygla', 'Glyinf': 'Glyinf',
    'Gmax_Jack': 'Jack', 'Gmax_WM82': 'WM82', 'Gmax_ZH13': 'ZH13',
    'Gsoj': 'Gsoj', 'Lpur': 'Lpur', 'Lsat': 'Lsat',
    'Mrub': 'Mrub', 'Msat': 'Msat',
    'Mtru_A17': 'A17', 'Mtru_R108': 'R108',
    'Pvul': 'Pvul', 'Tind': 'Tind', 'Vrad': 'Vrad',
}

# Region encoding
REGION_ARM     = 0
REGION_PERICEN = 1
REGION_CEN     = 2

REGION_MAP = {
    'Arm':             REGION_ARM,
    'Pericentromere':  REGION_PERICEN,
    'Centromere':      REGION_CEN,
}

# Superfamily colour palette
SUPERFAMILY_COLORS = {
    'Ogre':    '#E53935', 'Tekay': '#43A047', 'SIRE':  '#1E88E5',
    'Athila':  '#8E24AA', 'Ivana': '#FB8C00', 'Ale':   '#00ACC1',
    'Angela':  '#F4511E', 'Bianca':'#C0CA33', 'CRM':   '#3949AB',
    'Ikeros':  '#6D4C41', 'Reina': '#00897B', 'Retand':'#546E7A',
    'TAR':     '#D81B60', 'Tork':  '#5E35B1', 'Unclassified': '#9E9E9E',
}
DEFAULT_SF_COLOR = '#78909C'

REGION_TRACK_COLORS = {
    'Arm':             '#E0E0E0',
    'Pericentromere':  '#FFE0B2',
    'Centromere':      '#BBDEFB',
}

REGION_POINT_COLORS = {
    0: '#9E9E9E',   # Arm – gray
    1: '#FF9800',   # PeriCEN – orange
    2: '#1976D2',   # CEN – blue
}
