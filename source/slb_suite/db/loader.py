"""Data loader: parses TSVs/FASTA and populates SQLite databases."""

import csv
import sqlite3
import os
import re
import logging

from slb_suite.utils.config import (
    CEN_TSV_DIR, ARM_TSV_DIR, LTR_LIB_DIR,
    GENOME_INDEX_DIR, CEN_FASTA_DIR, ARM_FASTA_DIR,
    CEN_BED_DIR, GENOME_INFO_FILE, SOURCE_DIR,
    LTR_DB_PATH, ANNO_DB_PATH, REGION_MAP, SPECIES_LIB_MAP,
)

logger = logging.getLogger(__name__)


def _natural_sort_key(name: str) -> tuple:
    """Natural sort key for chromosome names (chr1, chr2, ..., chr10, etc.)."""
    parts = re.split(r"(\d+)", name)
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p)))
        else:
            key.append((1, p.lower()))
    return tuple(key)


# ── TSV parsing ───────────────────────────────────────────────────────────

def _parse_tsv(filepath: str, species: str, region_default: str) -> list[dict]:
    """Parse a TSV file and return list of row dicts."""
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            row["species"] = species
            row["region"] = row.get("Region", row.get("region", region_default)).strip()
            row["region_code"] = REGION_MAP.get(row["region"], 0)
            for int_col in ("start", "end", "aln_length", "mismatch", "gap"):
                try:
                    row[int_col] = int(row[int_col])
                except (ValueError, KeyError):
                    row[int_col] = 0
            for float_col in ("te_sorter_score", "pident", "evalue", "bitscore"):
                try:
                    row[float_col] = float(row[float_col])
                except (ValueError, KeyError):
                    row[float_col] = 0.0
            rows.append(row)
    return rows


# ── Genome index loading (.fa.fai) ─────────────────────────────────────────

def _load_genome_index(conn: sqlite3.Connection) -> set[str]:
    """Load chromosome lengths from .fa.fai files. Returns species set."""
    species_set = set()
    for fname in sorted(os.listdir(GENOME_INDEX_DIR)):
        if not fname.endswith(".fa.fai"):
            continue
        species = fname.replace(".fa.fai", "")
        species_set.add(species)
        filepath = os.path.join(GENOME_INDEX_DIR, fname)
        rows = []
        with open(filepath, "r") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    rows.append((species, parts[0], int(parts[1])))
        conn.executemany(
            "INSERT OR REPLACE INTO genome_index (species, chr, length) VALUES (?, ?, ?)",
            rows,
        )
        logger.info("Genome index: %s — %d chromosomes", species, len(rows))
    conn.commit()
    return species_set


# ── SoloLTR sequence ID lookup ─────────────────────────────────────────────

def _load_sololtr_lookup(conn: sqlite3.Connection):
    """Load SoloLTR sequence IDs for type annotation in BLAST results."""
    entries = []

    def _scan_fasta(fasta_dir, species, ltr_type):
        for fname in sorted(os.listdir(fasta_dir)):
            if not fname.endswith(".fa"):
                continue
            sp = fname.replace("_CEN_PeriCEN_SoloLTR.fa", "").replace("_Arm_SoloLTR.fa", "")
            if species and sp != species:
                continue
            filepath = os.path.join(fasta_dir, fname)
            count = 0
            with open(filepath, "r") as f:
                for line in f:
                    if line.startswith(">"):
                        seq_id = line[1:].strip().split()[0]
                        entries.append((seq_id, sp, ltr_type))
                        count += 1
            logger.info("SoloLTR lookup: %s — %d sequences (%s)", sp, count, ltr_type)

    _scan_fasta(CEN_FASTA_DIR, None, "CEN_PeriCEN_SoloLTR")
    _scan_fasta(ARM_FASTA_DIR, None, "Arm_SoloLTR")

    if entries:
        conn.executemany(
            "INSERT OR REPLACE INTO sololtr_lookup (seq_id, species, ltr_type) VALUES (?, ?, ?)",
            entries,
        )
        conn.commit()
    logger.info("SoloLTR lookup table: %d total entries", len(entries))


def _insert_ltr_rows(conn: sqlite3.Connection, rows: list[dict]):
    """Batch insert LTR rows."""
    sql = """
        INSERT INTO ltr_insertions
            (species, chr, start, end, solo_id, ref_ltr, te_sorter_score,
             target_ltr_id, pident, aln_length, mismatch, gap,
             evalue, bitscore, superfamily, region, region_code, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    data = [
        (
            r["species"], r["chr"], r["start"], r["end"], r["solo_id"],
            r.get("ref_ltr", ""), r.get("te_sorter_score", 0),
            r.get("target_ltr_id", ""), r.get("pident", 0),
            r.get("aln_length", 0), r.get("mismatch", 0), r.get("gap", 0),
            r.get("evalue", 0), r.get("bitscore", 0),
            r.get("Superfamily", r.get("superfamily", "")),
            r["region"], r["region_code"],
            r.get("Confidence", r.get("confidence", "")),
        )
        for r in rows
    ]
    conn.executemany(sql, data)


# ── Main loading function ──────────────────────────────────────────────────

def load_all_data(ltr_conn: sqlite3.Connection, anno_conn: sqlite3.Connection):
    """Load all data into databases."""
    from slb_suite.db.schema import CREATE_TABLES_SQL, CREATE_INDEXES_SQL

    for sql in CREATE_TABLES_SQL:
        ltr_conn.execute(sql)
        anno_conn.execute(sql)
    for sql in CREATE_INDEXES_SQL:
        try:
            ltr_conn.execute(sql)
        except sqlite3.OperationalError:
            pass
        try:
            anno_conn.execute(sql)
        except sqlite3.OperationalError:
            pass

    # 1. Load genome index
    _load_genome_index(ltr_conn)

    # 2. Load TSV annotations
    species_set = set()
    for fname in sorted(os.listdir(CEN_TSV_DIR)):
        if not fname.endswith("_CEN_PeriCEN_SoloLTR.tsv"):
            continue
        species = fname.replace("_CEN_PeriCEN_SoloLTR.tsv", "")
        species_set.add(species)
        logger.info("Loading CEN: %s", fname)
        rows = _parse_tsv(os.path.join(CEN_TSV_DIR, fname), species, "Pericentromere")
        _insert_ltr_rows(ltr_conn, rows)

    for fname in sorted(os.listdir(ARM_TSV_DIR)):
        if not fname.endswith("_Arm_SoloLTR.tsv"):
            continue
        species = fname.replace("_Arm_SoloLTR.tsv", "")
        species_set.add(species)
        logger.info("Loading Arm: %s", fname)
        rows = _parse_tsv(os.path.join(ARM_TSV_DIR, fname), species, "Arm")
        _insert_ltr_rows(ltr_conn, rows)

    ltr_conn.commit()

    # 3. Populate annotation.sqlite
    cur = ltr_conn.execute(
        "SELECT DISTINCT species, chr, region, region_code FROM ltr_insertions"
    )
    for species, chr_name, region, region_code in cur.fetchall():
        anno_conn.execute(
            "INSERT OR IGNORE INTO regions (species, chr, region_type, region_code) VALUES (?, ?, ?, ?)",
            (species, chr_name, region, region_code),
        )
    anno_conn.commit()

    # 4. Compute stats
    _compute_stats(ltr_conn)

    # 5. Load SoloLTR lookup table
    _load_sololtr_lookup(ltr_conn)

    # 6. Load CEN BED regions
    _load_cen_bed(ltr_conn)

    # 7. Load genome information
    _load_genome_info(ltr_conn)

    return sorted(species_set)


def _load_cen_bed(conn: sqlite3.Connection):
    """Load centromere BED files for precise CEN boundary annotation."""
    if not os.path.isdir(CEN_BED_DIR):
        logger.info("CEN BED directory not found, skipping")
        return
    entries = []
    for fname in sorted(os.listdir(CEN_BED_DIR)):
        if not fname.endswith(".bed"):
            continue
        species = fname.replace(".bed", "")
        filepath = os.path.join(CEN_BED_DIR, fname)
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("track"):
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                chr_name = parts[0]
                try:
                    s, e = int(parts[1]), int(parts[2])
                except ValueError:
                    continue
                entries.append((species, chr_name, s, e))
        logger.info("CEN BED: %s — %d regions", species, len(entries) if entries else 0)

    if entries:
        conn.executemany(
            "INSERT OR REPLACE INTO cen_bed_regions (species, chr, cen_start, cen_end) VALUES (?, ?, ?, ?)",
            entries,
        )
        conn.commit()
    logger.info("CEN BED regions: %d total entries", len(entries))


def _load_genome_info(conn: sqlite3.Connection):
    """Load genome information from genome_information.txt + Source directory."""
    if not os.path.isfile(GENOME_INFO_FILE):
        logger.info("genome_information.txt not found, skipping")
        return

    # Scan Source directory for PDF files and extract article titles
    source_files: dict[str, str] = {}
    source_titles: dict[str, str] = {}
    if os.path.isdir(SOURCE_DIR):
        for fname in sorted(os.listdir(SOURCE_DIR)):
            if not fname.endswith(".pdf"):
                continue
            filepath = os.path.join(SOURCE_DIR, fname)
            # Extract title from PDF metadata / first page
            title = _extract_pdf_title(filepath)
            # Filename may encode multiple species (e.g., Mtru_A17__Mtru_R108.pdf)
            stem = fname.replace(".pdf", "")
            for sp_code in stem.split("__"):
                sp_code = sp_code.strip()
                if sp_code:
                    source_files[sp_code] = fname
                    if title:
                        source_titles[sp_code] = title
        logger.info("Source files: %d species reference PDFs", len(source_files))

    entries = []
    with open(GENOME_INFO_FILE, "r", encoding="utf-8") as f:
        lines = list(f)
    if len(lines) < 3:
        logger.info("genome_information.txt too short, skipping")
        return
    header_line = ""
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith("ID\t") or line.startswith("ID\tSpecices"):
            header_line = line
            data_start = i + 1
            break
    if not header_line:
        logger.info("genome_information.txt header not found, skipping")
        return

    reader = csv.DictReader(lines[data_start:], delimiter="\t",
                            fieldnames=header_line.strip().split("\t"))
    for row in reader:
        sp_id = row.get("ID", "").strip()
        if not sp_id:
            continue
        latin = row.get("Specices", "").strip()
        if not latin:
            continue

        def _to_float(k):
            try:
                return float(row.get(k, 0) or 0)
            except ValueError:
                return 0.0

        def _to_int(k):
            try:
                return int(row.get(k, 0) or 0)
            except ValueError:
                return 0

        sf = source_files.get(sp_id, "")
        st = source_titles.get(sp_id, "")

        entries.append((
            sp_id, latin,
            _to_float("Assembly_size"),
            _to_int("Scaffold_number"),
            _to_float("Longest_scaffold/Mb"),
            _to_float("Scaffold_N50/ Mb"),
            _to_float("Contig_N50/ Mb"),
            _to_int("Gap_number"),
            _to_float("GC_content %"),
            _to_float("BUSCO %"),
            _to_int("Gapped centromere"),
            row.get("Source", "").strip(),
            sf,
            st,
        ))

    if entries:
        conn.executemany(
            """INSERT OR REPLACE INTO genome_info
               (species, latin_name, assembly_size, scaffold_number, longest_scaffold,
                scaffold_n50, contig_n50, gap_number, gc_content, busco, gapped_centromere,
                source, source_file, source_title)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            entries,
        )
        conn.commit()
        logger.info("Genome info: %d species loaded", len(entries))
    else:
        logger.info("Genome info: 0 species loaded")


def _extract_pdf_title(filepath: str) -> str:
    """Extract article title from a PDF file."""
    import html as _html
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        meta = reader.metadata
        title = None
        if meta:
            title = meta.get("/Title", None)
        if not title:
            page0 = reader.pages[0]
            text = page0.extract_text()
            if text:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if lines:
                    title = lines[0]
        if title:
            title = _html.unescape(title.strip())
            title = " ".join(title.split())
        return title or ""
    except Exception:
        return ""


def _compute_stats(conn: sqlite3.Connection):
    stats = conn.execute("""
        SELECT species,
               COUNT(*) AS total,
               SUM(CASE WHEN region_code = 2 THEN 1 ELSE 0 END) AS cen,
               SUM(CASE WHEN region_code = 1 THEN 1 ELSE 0 END) AS pericen,
               SUM(CASE WHEN region_code = 0 THEN 1 ELSE 0 END) AS arm
        FROM ltr_insertions GROUP BY species
    """).fetchall()
    conn.executemany(
        "INSERT OR REPLACE INTO species_stats (species, total_ltr, cen_ltr, pericen_ltr, arm_ltr) VALUES (?, ?, ?, ?, ?)",
        [(s, t, c, p, a) for s, t, c, p, a in stats],
    )
    conn.commit()


# ── Public query helpers ───────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(LTR_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_anno_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(ANNO_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def database_is_built() -> bool:
    if not os.path.exists(LTR_DB_PATH):
        return False
    conn = sqlite3.connect(LTR_DB_PATH)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ltr_insertions'")
    if cur.fetchone() is None:
        conn.close()
        return False
    cur = conn.execute("SELECT COUNT(*) FROM ltr_insertions")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def get_species_list() -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT species FROM ltr_insertions ORDER BY species").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_chromosomes(species: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT chr FROM ltr_insertions WHERE species=?", (species,)
    ).fetchall()
    conn.close()
    return sorted([r[0] for r in rows], key=_natural_sort_key)


def get_chromosome_length(species: str, chr_name: str) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT length FROM genome_index WHERE species=? AND chr=?",
        (species, chr_name),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def get_all_chromosome_lengths(species: str) -> dict[str, int]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT chr, length FROM genome_index WHERE species=?", (species,)
    ).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def get_ltrs_for_chromosome(species: str, chr_name: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ltr_insertions WHERE species=? AND chr=? ORDER BY start",
        (species, chr_name),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ltrs_in_range(species: str, chr_name: str, start: int, end: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM ltr_insertions
           WHERE species=? AND chr=? AND start >= ? AND end <= ?
           ORDER BY start""",
        (species, chr_name, start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats(species: str) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM species_stats WHERE species=?", (species,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"total_ltr": 0, "cen_ltr": 0, "pericen_ltr": 0, "arm_ltr": 0}


def get_all_stats() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM species_stats ORDER BY species").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ltr_library_path(species: str) -> str:
    """Get the FASTA file path for a species LTR library."""
    lib_dir_name = SPECIES_LIB_MAP.get(species, species)
    lib_dir = os.path.join(LTR_LIB_DIR, lib_dir_name)
    if not os.path.isdir(lib_dir):
        return ""
    for fname in os.listdir(lib_dir):
        if fname.endswith(".fasta") or fname.endswith(".fa"):
            return os.path.join(lib_dir, fname)
    return ""


def solo_ltr_fasta_paths(species: str) -> list[str]:
    """Get SoloLTR FASTA paths for a species (both CEN and Arm)."""
    paths = []
    cen_file = os.path.join(CEN_FASTA_DIR, f"{species}_CEN_PeriCEN_SoloLTR.fa")
    arm_file = os.path.join(ARM_FASTA_DIR, f"{species}_Arm_SoloLTR.fa")
    if os.path.isfile(cen_file):
        paths.append(cen_file)
    if os.path.isfile(arm_file):
        paths.append(arm_file)
    return paths


def get_seq_type_lookup(species: str) -> dict[str, str]:
    """Get mapping of sequence ID -> type (SoloLTR/Complete_LTR) for a species."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT seq_id, ltr_type FROM sololtr_lookup WHERE species=?",
        (species,),
    ).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def get_cen_bed_regions(species: str) -> dict[str, tuple[int, int]]:
    """Get centromere BED regions for a species. Returns dict of chr -> (start, end)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT chr, cen_start, cen_end FROM cen_bed_regions WHERE species=?",
        (species,),
    ).fetchall()
    conn.close()
    return {r[0]: (r[1], r[2]) for r in rows}


def get_genome_info(species: str) -> dict | None:
    """Get genome information for a species."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM genome_info WHERE species=?", (species,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_genome_info() -> dict[str, dict]:
    """Get genome information for all species. Returns dict of species -> info."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM genome_info ORDER BY species").fetchall()
    conn.close()
    return {r["species"]: dict(r) for r in rows}
