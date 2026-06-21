"""BLAST engine: combined database from NR library + SoloLTR FASTA, with type annotation."""

import os
import sys
import subprocess
import tempfile
import logging

from slb_suite.utils.config import BLAST_DB_DIR
from slb_suite.db.loader import ltr_library_path, solo_ltr_fasta_paths

logger = logging.getLogger(__name__)


def _find_executable(name: str) -> str:
    # 1. Packaged mode — bundled blast/ directory next to the executable
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        bundled = os.path.join(exe_dir, 'blast', name)
        if sys.platform == 'darwin':
            # .app/Contents/MacOS/ -> .app/Contents/Resources/blast/
            bundled = os.path.join(os.path.dirname(exe_dir), 'Resources', 'blast', name)
        if os.path.isfile(bundled) and os.access(bundled, os.X_OK):
            return bundled
        # Windows: add .exe if needed
        if sys.platform == 'win32' and not name.endswith('.exe'):
            bundled_exe = bundled + '.exe'
            if os.path.isfile(bundled_exe):
                return bundled_exe

    # 2. PATH search
    result = subprocess.run(['which', name], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    # 3. Common install prefixes
    for prefix in ['/usr/bin', '/usr/local/bin', '/opt/conda/bin']:
        path = os.path.join(prefix, name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return ""


def _build_combined_fasta(species: str) -> tuple[str, dict[str, str], bool]:
    """Build a combined FASTA file with type-tagged sequences.

    Returns (combined_fasta_path, seq_id_to_type_map, success).
    """
    safe_name = species.replace("/", "_").replace(" ", "_")
    db_dir = os.path.join(BLAST_DB_DIR, safe_name)
    os.makedirs(db_dir, exist_ok=True)
    combined_path = os.path.join(db_dir, f"{safe_name}_combined.fa")

    # Check if already built
    if os.path.exists(combined_path):
        # Rebuild the type map
        type_map = {}
        type_map.update(_read_seq_types_from_fasta(combined_path))
        if type_map:
            return combined_path, type_map, True

    type_map = {}
    seq_count = {"Complete_LTR": 0, "SoloLTR": 0}

    with open(combined_path, "w") as out_f:
        # 1. NR LTR library (complete LTR elements)
        lib_path = ltr_library_path(species)
        if lib_path:
            with open(lib_path, "r") as in_f:
                for line in in_f:
                    if line.startswith(">"):
                        seq_id = line[1:].strip().split()[0]
                        mapped_id = f"COMPLETE|{seq_id}"
                        type_map[mapped_id] = "Complete_LTR"
                        type_map[seq_id] = "Complete_LTR"
                        out_f.write(f">{mapped_id}\n")
                        seq_count["Complete_LTR"] += 1
                    else:
                        out_f.write(line)

        # 2. SoloLTR FASTA sequences
        for solo_path in solo_ltr_fasta_paths(species):
            with open(solo_path, "r") as in_f:
                for line in in_f:
                    if line.startswith(">"):
                        seq_id = line[1:].strip().split()[0]
                        mapped_id = f"SOLOLTR|{seq_id}"
                        type_map[mapped_id] = "SoloLTR"
                        type_map[seq_id] = "SoloLTR"
                        out_f.write(f">{mapped_id}\n")
                        seq_count["SoloLTR"] += 1
                    else:
                        out_f.write(line)

    if seq_count["Complete_LTR"] == 0 and seq_count["SoloLTR"] == 0:
        return "", {}, False

    logger.info(
        "Combined FASTA for %s: %d Complete_LTR + %d SoloLTR sequences",
        species, seq_count["Complete_LTR"], seq_count["SoloLTR"],
    )
    return combined_path, type_map, True


def _read_seq_types_from_fasta(fasta_path: str) -> dict[str, str]:
    """Read type tags from a combined FASTA file headers."""
    type_map = {}
    with open(fasta_path, "r") as f:
        for line in f:
            if line.startswith(">"):
                header = line[1:].strip().split()[0]
                if header.startswith("COMPLETE|"):
                    type_map[header] = "Complete_LTR"
                    type_map[header.split("|", 1)[1]] = "Complete_LTR"
                elif header.startswith("SOLOLTR|"):
                    type_map[header] = "SoloLTR"
                    type_map[header.split("|", 1)[1]] = "SoloLTR"
    return type_map


def build_blast_db(species: str) -> tuple[bool, str]:
    """Build combined BLAST database for a species.
    Returns (success, db_path_or_error).
    """
    combined_fa, type_map, ok = _build_combined_fasta(species)
    if not ok:
        return False, f"No sequences found for species: {species}"

    makeblastdb = _find_executable("makeblastdb")
    if not makeblastdb:
        return False, "makeblastdb not found. Please install BLAST+."

    safe_name = species.replace("/", "_").replace(" ", "_")
    db_dir = os.path.join(BLAST_DB_DIR, safe_name)
    db_base = os.path.join(db_dir, safe_name)

    # Check if BLAST DB already built
    if os.path.exists(db_base + ".nin"):
        return True, db_base

    cmd = [
        makeblastdb, "-in", combined_fa, "-dbtype", "nucl",
        "-out", db_base, "-title", f"LTR_combined_{safe_name}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                                cwd=os.path.dirname(makeblastdb))
        if result.returncode == 0:
            return True, db_base
        else:
            return False, result.stderr or result.stdout
    except subprocess.TimeoutExpired:
        return False, "makeblastdb timed out"
    except FileNotFoundError:
        return False, "makeblastdb not found"


def run_blast(species: str, query: str, evalue: float = 1e-5,
              max_hits: int = 100) -> tuple[bool, list[dict] | str]:
    """Run blastn against combined LTR database.
    Returns (success, results_list_or_error).
    Results include 'ltr_type' field: 'Complete_LTR' or 'SoloLTR'.
    """
    ok, db_path = build_blast_db(species)
    if not ok:
        return False, db_path

    blastn = _find_executable("blastn")
    if not blastn:
        return False, "blastn not found."

    query = query.strip()
    if not query:
        return False, "Empty query sequence"

    # Load type map
    safe_name = species.replace("/", "_").replace(" ", "_")
    db_dir = os.path.join(BLAST_DB_DIR, safe_name)
    combined_fa = os.path.join(db_dir, f"{safe_name}_combined.fa")
    type_map = _read_seq_types_from_fasta(combined_fa)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as f:
        f.write(query if query.startswith(">") else ">query\n" + query + "\n")
        query_file = f.name

    try:
        cmd = [
            blastn, "-db", db_path, "-query", query_file,
            "-evalue", str(evalue), "-max_target_seqs", str(max_hits),
            "-outfmt", "6 qseqid sseqid pident evalue bitscore length mismatch gapopen qstart qend sstart send",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                                cwd=os.path.dirname(blastn))

        if result.returncode != 0:
            return False, result.stderr or "blastn failed"

        hits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) < 12:
                continue

            sseqid_tagged = fields[1]
            # Determine LTR type from tagged ID
            ltr_type = "Unknown"
            clean_sseqid = sseqid_tagged
            if sseqid_tagged.startswith("COMPLETE|"):
                ltr_type = "Complete_LTR"
                clean_sseqid = sseqid_tagged.split("|", 1)[1]
            elif sseqid_tagged.startswith("SOLOLTR|"):
                ltr_type = "SoloLTR"
                clean_sseqid = sseqid_tagged.split("|", 1)[1]
            elif sseqid_tagged in type_map:
                ltr_type = type_map[sseqid_tagged]

            # Parse SoloLTR header for metadata
            solo_species = ""
            solo_superfamily = ""
            solo_region = ""
            solo_chr = ""
            solo_start = 0
            solo_end = 0
            if ltr_type == "SoloLTR":
                parts = clean_sseqid.split("|")
                if len(parts) >= 4:
                    solo_species = parts[0]
                    solo_superfamily = parts[1]
                    solo_region = parts[2]
                    loc_part = parts[3]
                    if ":" in loc_part:
                        chr_part, coords = loc_part.rsplit(":", 1)
                        solo_chr = chr_part
                        if ".." in coords:
                            try:
                                s, e = coords.split("..")
                                solo_start = int(s)
                                solo_end = int(e)
                            except ValueError:
                                pass

            hit = {
                "qseqid": fields[0],
                "sseqid": clean_sseqid,
                "sseqid_tagged": sseqid_tagged,
                "ltr_type": ltr_type,
                "pident": float(fields[2]),
                "evalue": float(fields[3]),
                "bitscore": float(fields[4]),
                "length": int(fields[5]),
                "mismatch": int(fields[6]),
                "gapopen": int(fields[7]),
                "qstart": int(fields[8]),
                "qend": int(fields[9]),
                "sstart": int(fields[10]),
                "send": int(fields[11]),
                "solo_species": solo_species,
                "solo_superfamily": solo_superfamily,
                "solo_region": solo_region,
                "solo_chr": solo_chr,
                "solo_start": solo_start,
                "solo_end": solo_end,
            }
            hits.append(hit)

        # Annotate with genomic location from ltr.sqlite
        _annotate_hits(species, hits)
        return True, hits

    except subprocess.TimeoutExpired:
        return False, "BLAST search timed out"
    finally:
        if os.path.exists(query_file):
            os.unlink(query_file)


def _annotate_hits(species: str, hits: list[dict]):
    """Add genomic location info to BLAST hits by querying ltr.sqlite."""
    from slb_suite.utils.config import LTR_DB_PATH
    import sqlite3

    if not hits:
        return

    # For SoloLTR hits, we already have coordinates from the FASTA header
    # For Complete_LTR hits, look up genomic locations where this LTR is annotated
    complete_hits = [h for h in hits if h["ltr_type"] == "Complete_LTR"]
    if not complete_hits:
        return

    target_ids = list(set(h["sseqid"] for h in complete_hits))
    if not target_ids:
        return

    try:
        conn = sqlite3.connect(LTR_DB_PATH)
        conn.row_factory = sqlite3.Row

        # Build lookup from target_ltr_id (which is the complete LTR ID used in annotation)
        placeholders = ",".join(["?" for _ in target_ids])
        rows = conn.execute(
            f"""SELECT DISTINCT target_ltr_id, chr, start, end, region, superfamily
                FROM ltr_insertions
                WHERE species=? AND target_ltr_id IN ({placeholders})""",
            [species] + target_ids,
        ).fetchall()
        conn.close()

        lookup = {}
        for r in rows:
            key = r["target_ltr_id"]
            if key not in lookup:
                lookup[key] = {
                    "chr": r["chr"], "start": r["start"], "end": r["end"],
                    "region": r["region"], "superfamily": r["superfamily"],
                }

        for hit in complete_hits:
            loc = lookup.get(hit["sseqid"])
            if loc:
                hit["genomic_chr"] = loc["chr"]
                hit["genomic_start"] = loc["start"]
                hit["genomic_end"] = loc["end"]
                hit["genomic_region"] = loc["region"]
                hit["genomic_superfamily"] = loc["superfamily"]
            else:
                hit["genomic_chr"] = "N/A"
                hit["genomic_start"] = 0
                hit["genomic_end"] = 0
                hit["genomic_region"] = "N/A"
                hit["genomic_superfamily"] = ""
    except Exception:
        for hit in complete_hits:
            hit["genomic_chr"] = "N/A"
            hit["genomic_start"] = 0
            hit["genomic_end"] = 0
            hit["genomic_region"] = "N/A"
            hit["genomic_superfamily"] = ""

    # For SoloLTR hits, fill genomic fields from parsed coordinates
    for hit in hits:
        if hit["ltr_type"] == "SoloLTR":
            hit["genomic_chr"] = hit.get("solo_chr", "N/A")
            hit["genomic_start"] = hit.get("solo_start", 0)
            hit["genomic_end"] = hit.get("solo_end", 0)
            hit["genomic_region"] = hit.get("solo_region", "N/A")
            hit["genomic_superfamily"] = hit.get("solo_superfamily", "")


def get_sequence_for_hit(species: str, sseqid_tagged: str) -> tuple[str, str]:
    """Retrieve the FASTA sequence for a BLAST hit.
    Returns (header, sequence) or ("", "") if not found.
    """
    safe_name = species.replace("/", "_").replace(" ", "_")
    db_dir = os.path.join(BLAST_DB_DIR, safe_name)
    combined_fa = os.path.join(db_dir, f"{safe_name}_combined.fa")

    if not os.path.isfile(combined_fa):
        return "", ""

    try:
        with open(combined_fa, "r") as f:
            found = False
            header = ""
            seq_lines = []
            for line in f:
                if line.startswith(">"):
                    if found:
                        break
                    hdr = line[1:].strip().split()[0]
                    if hdr == sseqid_tagged:
                        found = True
                        header = line[1:].strip()
                elif found:
                    seq_lines.append(line.strip())
            if found:
                return header, "".join(seq_lines)
    except Exception:
        pass
    return "", ""
