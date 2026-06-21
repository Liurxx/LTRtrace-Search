"""SQLite schema definitions for ltr.sqlite and annotation.sqlite."""

CREATE_LTR_TABLE = """
CREATE TABLE IF NOT EXISTS ltr_insertions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species TEXT NOT NULL,
    chr TEXT NOT NULL,
    start INTEGER NOT NULL,
    end INTEGER NOT NULL,
    solo_id TEXT NOT NULL,
    ref_ltr TEXT,
    te_sorter_score REAL,
    target_ltr_id TEXT,
    pident REAL,
    aln_length INTEGER,
    mismatch INTEGER,
    gap INTEGER,
    evalue REAL,
    bitscore REAL,
    superfamily TEXT,
    region TEXT NOT NULL,
    region_code INTEGER NOT NULL,
    confidence TEXT
);
"""

CREATE_LTR_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ltr_species ON ltr_insertions(species);",
    "CREATE INDEX IF NOT EXISTS idx_ltr_chr ON ltr_insertions(chr);",
    "CREATE INDEX IF NOT EXISTS idx_ltr_species_chr ON ltr_insertions(species, chr);",
    "CREATE INDEX IF NOT EXISTS idx_ltr_region_code ON ltr_insertions(region_code);",
    "CREATE INDEX IF NOT EXISTS idx_ltr_superfamily ON ltr_insertions(superfamily);",
    "CREATE INDEX IF NOT EXISTS idx_ltr_start_end ON ltr_insertions(chr, start, end);",
    "CREATE INDEX IF NOT EXISTS idx_ltr_target ON ltr_insertions(target_ltr_id);",
]

CREATE_GENOME_INDEX_TABLE = """
CREATE TABLE IF NOT EXISTS genome_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species TEXT NOT NULL,
    chr TEXT NOT NULL,
    length INTEGER NOT NULL,
    UNIQUE(species, chr)
);
"""

CREATE_GENOME_INDEX_INDEX = [
    "CREATE INDEX IF NOT EXISTS idx_genome_species ON genome_index(species);",
    "CREATE INDEX IF NOT EXISTS idx_genome_species_chr ON genome_index(species, chr);",
]

CREATE_ANNOTATION_TABLE = """
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species TEXT NOT NULL,
    chr TEXT NOT NULL,
    region_type TEXT NOT NULL,
    region_code INTEGER NOT NULL
);
"""

CREATE_ANNO_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_anno_species ON regions(species);",
    "CREATE INDEX IF NOT EXISTS idx_anno_species_chr ON regions(species, chr);",
]

CREATE_STATS_TABLE = """
CREATE TABLE IF NOT EXISTS species_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species TEXT NOT NULL UNIQUE,
    total_ltr INTEGER DEFAULT 0,
    cen_ltr INTEGER DEFAULT 0,
    pericen_ltr INTEGER DEFAULT 0,
    arm_ltr INTEGER DEFAULT 0
);
"""

CREATE_SOLOLTR_LOOKUP_TABLE = """
CREATE TABLE IF NOT EXISTS sololtr_lookup (
    seq_id TEXT PRIMARY KEY,
    species TEXT NOT NULL,
    ltr_type TEXT NOT NULL,
    UNIQUE(seq_id)
);
"""

CREATE_SOLOLTR_LOOKUP_INDEX = [
    "CREATE INDEX IF NOT EXISTS idx_sololtr_species ON sololtr_lookup(species);",
    "CREATE INDEX IF NOT EXISTS idx_sololtr_type ON sololtr_lookup(ltr_type);",
]

CREATE_CEN_BED_TABLE = """
CREATE TABLE IF NOT EXISTS cen_bed_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species TEXT NOT NULL,
    chr TEXT NOT NULL,
    cen_start INTEGER NOT NULL,
    cen_end INTEGER NOT NULL,
    UNIQUE(species, chr)
);
"""

CREATE_CEN_BED_INDEX = [
    "CREATE INDEX IF NOT EXISTS idx_cen_bed_species ON cen_bed_regions(species);",
    "CREATE INDEX IF NOT EXISTS idx_cen_bed_species_chr ON cen_bed_regions(species, chr);",
]

CREATE_GENOME_INFO_TABLE = """
CREATE TABLE IF NOT EXISTS genome_info (
    species TEXT PRIMARY KEY,
    latin_name TEXT NOT NULL,
    assembly_size REAL,
    scaffold_number INTEGER,
    longest_scaffold REAL,
    scaffold_n50 REAL,
    contig_n50 REAL,
    gap_number INTEGER,
    gc_content REAL,
    busco REAL,
    gapped_centromere INTEGER,
    source TEXT,
    source_file TEXT,
    source_title TEXT
);
"""

CREATE_GENOME_INFO_INDEX = [
    "CREATE INDEX IF NOT EXISTS idx_genome_info_species ON genome_info(species);",
]

CREATE_TABLES_SQL = [
    CREATE_LTR_TABLE, CREATE_GENOME_INDEX_TABLE,
    CREATE_ANNOTATION_TABLE, CREATE_STATS_TABLE, CREATE_SOLOLTR_LOOKUP_TABLE,
    CREATE_CEN_BED_TABLE, CREATE_GENOME_INFO_TABLE,
]
CREATE_INDEXES_SQL = (
    CREATE_LTR_INDEXES + CREATE_GENOME_INDEX_INDEX +
    CREATE_ANNO_INDEXES + CREATE_SOLOLTR_LOOKUP_INDEX +
    CREATE_CEN_BED_INDEX + CREATE_GENOME_INFO_INDEX
)
