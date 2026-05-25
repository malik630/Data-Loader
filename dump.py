"""
generate_sample_dumps.py
Sprint 3 – Team 3 | Topic M6 | Team SG03

Generates two sample dump SQL files:
  - sample_dump_postgres.sql      (m6_thermal)
  - sample_dump_timescaledb.sql   (m6_thermal_tsdb)

Each file contains INSERT statements for patient_id IN (0, 1).

Usage:
    pip install psycopg2-binary
    python generate_sample_dumps.py
"""

import psycopg2
from datetime import datetime

# ── DB connections ────────────────────────────────────────────────────────────
PG_CONN = dict(host="localhost", port=5432, user="postgres", password="ches758queen", dbname="m6_thermal")
TSDB_CONN = dict(host="localhost", port=5432, user="postgres", password="ches758queen", dbname="m6_thermal_tsdb")

PATIENT_IDS = (0, 1)

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_val(v):
    """Format a Python value as a SQL literal."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, datetime):
        return f"'{v.isoformat()}'"
    return f"'{str(v).replace(chr(39), chr(39)*2)}'"


def dump_table(cur, table, where_clause, output_lines, limit=None):
    """Fetch rows from table and append INSERT statements to output_lines."""
    query = f"SELECT * FROM {table} WHERE {where_clause}"
    if limit:
        query += f" LIMIT {limit}"
    cur.execute(query)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]

    if not rows:
        output_lines.append(f"-- No data found in {table} for patient_id IN {PATIENT_IDS}\n")
        return

    output_lines.append(f"-- {table} ({len(rows)} rows)\n")
    for row in rows:
        vals = ", ".join(fmt_val(v) for v in row)
        col_list = ", ".join(cols)
        output_lines.append(f"INSERT INTO {table} ({col_list}) VALUES ({vals}) ON CONFLICT DO NOTHING;\n")
    output_lines.append("\n")


def write_header(lines, db_name, db_type):
    lines.append(f"-- =============================================================================\n")
    lines.append(f"-- sample_dump_{db_type}.sql\n")
    lines.append(f"-- Sprint 3 – Team 3 | Topic M6 | Team SG03\n")
    lines.append(f"-- Sample data dump: patient_id IN {PATIENT_IDS}\n")
    lines.append(f"-- Generated: {datetime.now().isoformat()}\n")
    lines.append(f"-- Database: {db_name}\n")
    lines.append(f"-- Restore: psql -U postgres -d {db_name} -f sample_dump_{db_type}.sql\n")
    lines.append(f"-- =============================================================================\n\n")


# ── PostgreSQL dump ───────────────────────────────────────────────────────────

def generate_postgres_dump():
    print("[PostgreSQL] Connecting...")
    conn = psycopg2.connect(**PG_CONN)
    cur = conn.cursor()

    lines = []
    write_header(lines, PG_CONN["dbname"], "postgres")

    where = f"patient_id IN {PATIENT_IDS}"

    print("[PostgreSQL] Dumping subjects...")
    dump_table(cur, "subjects", where, lines)

    print("[PostgreSQL] Dumping recordings...")
    dump_table(cur, "recordings", where, lines)

    print("[PostgreSQL] Dumping windows (50 rows)...")
    dump_table(cur, "windows", where, lines, limit=50)

    # Get time range of the 50 windows to filter signals
    cur.execute(f"""
        SELECT MIN(window_start), MAX(window_end)
        FROM (SELECT window_start, window_end FROM windows WHERE {where} LIMIT 50) w
    """)
    ts_min, ts_max = cur.fetchone()

    print("[PostgreSQL] Dumping signals (within 50 windows time range)...")
    if ts_min and ts_max:
        sig_where = f"patient_id IN {PATIENT_IDS} AND timestamp BETWEEN '{ts_min}' AND '{ts_max}'"
        dump_table(cur, "signals", sig_where, lines)
    else:
        lines.append("-- signals: no time range found from windows\n\n")

    # attention_maps if exists and has data
    try:
        print("[PostgreSQL] Dumping attention_maps...")
        dump_table(cur, "attention_maps", where, lines)
    except Exception:
        lines.append("-- attention_maps: table empty or not yet populated\n\n")
        conn.rollback()

    cur.close()
    conn.close()

    with open("sample_dump_postgres.sql", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("[PostgreSQL] ✅ sample_dump_postgres.sql generated")


# ── TimescaleDB dump ──────────────────────────────────────────────────────────

def generate_timescaledb_dump():
    print("[TimescaleDB] Connecting...")
    conn = psycopg2.connect(**TSDB_CONN)
    cur = conn.cursor()

    lines = []
    write_header(lines, TSDB_CONN["dbname"], "timescaledb")

    where = f"patient_id IN {PATIENT_IDS}"

    print("[TimescaleDB] Dumping subjects...")
    dump_table(cur, "subjects", where, lines)

    print("[TimescaleDB] Dumping windows_tsdb (50 rows)...")
    dump_table(cur, "windows_tsdb", where, lines, limit=50)

    # Get time range
    cur.execute(f"""
        SELECT MIN(window_start), MAX(window_end)
        FROM (SELECT window_start, window_end FROM windows_tsdb WHERE {where} LIMIT 50) w
    """)
    ts_min, ts_max = cur.fetchone()

    print("[TimescaleDB] Dumping thermal_readings (within 50 windows time range)...")
    if ts_min and ts_max:
        tr_where = f"patient_id IN {PATIENT_IDS} AND timestamp BETWEEN '{ts_min}' AND '{ts_max}'"
        dump_table(cur, "thermal_readings", tr_where, lines)
    else:
        lines.append("-- thermal_readings: no time range found from windows_tsdb\n\n")

    # attention_maps if exists
    try:
        print("[TimescaleDB] Dumping attention_maps...")
        dump_table(cur, "attention_maps", where, lines)
    except Exception:
        lines.append("-- attention_maps: table empty or not yet populated\n\n")
        conn.rollback()

    cur.close()
    conn.close()

    with open("sample_dump_timescaledb.sql", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("[TimescaleDB] ✅ sample_dump_timescaledb.sql generated")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    generate_postgres_dump()
    generate_timescaledb_dump()
    print("\n✅ Done. Files: sample_dump_postgres.sql | sample_dump_timescaledb.sql")