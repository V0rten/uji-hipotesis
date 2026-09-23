#!/usr/bin/env python3
"""
Analisis fitur tunggal dengan RAM rendah menggunakan DuckDB.

Versi ini dibuat untuk dataset sliding-window besar, misalnya jutaan baris
Parquet. Script lama memuat seluruh dataset ke pandas lalu membuat banyak
copy DataFrame dan bucket per fitur. Itu dapat menghabiskan RAM belasan GB.

Script ini:
- membaca Parquet secara lazy melalui DuckDB;
- hanya mengambil kolom yang diperlukan;
- tidak memuat seluruh 8+ juta baris ke RAM;
- menghitung target t+1 melalui mapping kecil dari 410_kalibrasi.md;
- mengagregasi hasil langsung di DuckDB;
- menulis output kecil berupa tabel ringkasan.

Install:
    pip install duckdb pandas

Contoh:
    python single_feature_analysis.py \
        --raw 410_kalibrasi.md \
        --windows 410_kalibrasi10_2000_raw.parquet \
        --out feature_analysis

Jika dataset window sudah memiliki kolom target, opsi --raw tetap boleh
diberikan tetapi tidak diperlukan. Untuk efisiensi, gunakan Parquet, bukan CSV.

Output:
    feature_bucket_summary.csv
    feature_window_group_summary.csv
    top_features.csv
    feature_analysis_summary.json

Catatan metodologis:
- Window saling overlap, sehingga jutaan baris bukan jutaan sample independen.
- Hasil script ini adalah eksplorasi, bukan bukti prediktabilitas.
- Signal harus dicek lagi dengan validasi kronologis/walk-forward.
"""

from __future__ import annotations

import argparse
import json
from io import StringIO
from pathlib import Path

import duckdb
import pandas as pd

THRESHOLDS = [2, 5, 10, 20, 50, 100]
WINDOW_GROUP_CASE = """
CASE
  WHEN window_size <= 10 THEN '<=10'
  WHEN window_size <= 30 THEN '11-30'
  WHEN window_size <= 50 THEN '31-50'
  WHEN window_size <= 100 THEN '51-100'
  WHEN window_size <= 250 THEN '101-250'
  WHEN window_size <= 500 THEN '251-500'
  WHEN window_size <= 1000 THEN '501-1000'
  WHEN window_size <= 2000 THEN '1001-2000'
  ELSE '>2000'
END
"""


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RAM-efficient single-feature analysis")
    p.add_argument("--raw", type=Path, required=False, help="410_kalibrasi.md")
    p.add_argument("--windows", type=Path, required=True, help="CSV/Parquet windows")
    p.add_argument("--out", type=Path, default=Path("feature_analysis"))
    p.add_argument("--threads", type=int, default=2, help="DuckDB threads; default 2")
    p.add_argument("--memory-limit", default="4GB", help="DuckDB memory limit")
    return p.parse_args()


def read_raw(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8")
    lines = [x.strip() for x in text.splitlines() if x.lstrip().startswith("|")]
    if len(lines) < 3:
        raise ValueError(f"Tabel Markdown tidak ditemukan: {path}")

    normalized = []
    for line in lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        normalized.append("|" + "|".join(cells) + "|")

    raw = pd.read_csv(StringIO("\n".join(normalized)), sep="|", engine="python")
    raw = raw.dropna(axis=1, how="all")
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.loc[:, [c for c in raw.columns if c]]
    raw["game_id"] = pd.to_numeric(raw["game_id"], errors="coerce")
    raw["gr_result"] = pd.to_numeric(raw["gr_result"], errors="coerce")
    raw = raw.dropna(subset=["game_id", "gr_result"])
    raw["game_id"] = raw["game_id"].astype("int64")
    raw = raw.drop_duplicates("game_id").reset_index(drop=True)

    ids = raw["game_id"].tolist()
    next_ids = ids[1:] + [None]
    mapping = pd.DataFrame(
        {
            "last_game_id": ids,
            "target_game_id": next_ids,
            "target_gr": raw["gr_result"].tolist()[1:] + [None],
        }
    )
    return mapping


def sql_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def main() -> None:
    a = args()
    if a.windows.suffix.lower() not in {".parquet", ".csv"}:
        raise ValueError("--windows harus berupa .parquet atau .csv")
    if a.raw is None:
        raise ValueError("--raw diperlukan untuk membangun target t+1")

    a.out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.memory_limit}'")
    con.execute(f"SET threads={max(1, a.threads)}")
    con.execute("SET preserve_insertion_order=false")
    con.register("target_map", read_raw(a.raw))

    source = f"read_parquet('{a.windows.as_posix()}')" if a.windows.suffix.lower() == ".parquet" else f"read_csv_auto('{a.windows.as_posix()}', header=true)"
    cols = [x[0] for x in con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()]
    required = {"window_size", "last_game_id"}
    missing = required - set(cols)
    if missing:
        raise ValueError(f"Kolom window hilang: {sorted(missing)}")

    excluded = {
        "window_size", "window_no", "window_start", "window_end",
        "first_game_id", "last_game_id", "first_tag_ts", "first_tag_ts_iso",
        "last_ts_gr", "last_cat", "target_gr", "target_game_id",
    }
    features = [c for c in cols if c not in excluded and not c.startswith("target_")]
    # Hanya analisis kolom numerik/bool yang memang ada di schema.
    schema = {r[0]: r[1].upper() for r in con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()}
    features = [c for c in features if any(t in schema[c] for t in ("INT", "DECIMAL", "DOUBLE", "FLOAT", "BOOL", "HUGEINT"))]
    if not features:
        raise ValueError("Tidak ada fitur numerik/bool untuk dianalisis")

    feature_sql = ", ".join(sql_ident(c) for c in ["window_size", "last_game_id", *features])
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW base AS
        SELECT w.*, m.target_gr
        FROM (SELECT {feature_sql} FROM {source}) w
        LEFT JOIN target_map m ON CAST(w.last_game_id AS BIGINT) = m.last_game_id
        WHERE m.target_gr IS NOT NULL
    """)

    baseline = con.execute("""
        SELECT
          COUNT(*) AS n,
          AVG(target_gr >= 2) AS p_ge_2,
          AVG(target_gr >= 5) AS p_ge_5,
          AVG(target_gr >= 10) AS p_ge_10,
          AVG(target_gr >= 20) AS p_ge_20,
          AVG(target_gr >= 50) AS p_ge_50,
          AVG(target_gr >= 100) AS p_ge_100
        FROM base
    """).df().iloc[0].to_dict()

    all_rows = []
    group_rows = []
    for feature in features:
        f = sql_ident(feature)
        # approx_quantile menghindari qcut dan tidak membuat copy DataFrame besar.
        for group_filter, group_name in [("TRUE", "ALL"), *[(f"window_size > {lo} AND window_size <= {hi}", name) for lo, hi, name in [(10,30,"11-30"),(30,50,"31-50"),(50,100,"51-100"),(100,250,"101-250"),(250,500,"251-500"),(500,1000,"501-1000"),(1000,2000,"1001-2000")]]]:
            q = f"""
              WITH q AS (
                SELECT
                  approx_quantile(CAST({f} AS DOUBLE), 0.2) q20,
                  approx_quantile(CAST({f} AS DOUBLE), 0.4) q40,
                  approx_quantile(CAST({f} AS DOUBLE), 0.6) q60,
                  approx_quantile(CAST({f} AS DOUBLE), 0.8) q80
                FROM base WHERE {group_filter} AND {f} IS NOT NULL
              ), b AS (
                SELECT *, CASE
                  WHEN CAST({f} AS DOUBLE) <= q20 THEN 'q1'
                  WHEN CAST({f} AS DOUBLE) <= q40 THEN 'q2'
                  WHEN CAST({f} AS DOUBLE) <= q60 THEN 'q3'
                  WHEN CAST({f} AS DOUBLE) <= q80 THEN 'q4'
                  ELSE 'q5' END AS bucket
                FROM base, q
                WHERE {group_filter} AND {f} IS NOT NULL
              )
              SELECT '{feature}' feature, '{group_name}' window_group, bucket,
                COUNT(*) n,
                AVG(target_gr < 2) low_rate,
                AVG(target_gr >= 2) p_ge_2,
                AVG(target_gr >= 5) p_ge_5,
                AVG(target_gr >= 10) p_ge_10,
                AVG(target_gr >= 20) p_ge_20,
                AVG(target_gr >= 50) p_ge_50,
                AVG(target_gr >= 100) p_ge_100
              FROM b GROUP BY bucket ORDER BY bucket
            """
            group_rows.append(con.execute(q).df())

        q_all = group_rows[-1] if False else None
        # Global summary is derived from ALL rows with the same streaming query.
        global_q = f"""
          WITH q AS (
            SELECT approx_quantile(CAST({f} AS DOUBLE), 0.2) q20,
                   approx_quantile(CAST({f} AS DOUBLE), 0.4) q40,
                   approx_quantile(CAST({f} AS DOUBLE), 0.6) q60,
                   approx_quantile(CAST({f} AS DOUBLE), 0.8) q80
            FROM base WHERE {f} IS NOT NULL
          ), b AS (
            SELECT *, CASE WHEN CAST({f} AS DOUBLE)<=q20 THEN 'q1'
              WHEN CAST({f} AS DOUBLE)<=q40 THEN 'q2'
              WHEN CAST({f} AS DOUBLE)<=q60 THEN 'q3'
              WHEN CAST({f} AS DOUBLE)<=q80 THEN 'q4' ELSE 'q5' END bucket
            FROM base, q WHERE {f} IS NOT NULL
          )
          SELECT '{feature}' feature, bucket, COUNT(*) n,
            AVG(target_gr < 2) low_rate, AVG(target_gr >= 2) p_ge_2,
            AVG(target_gr >= 5) p_ge_5, AVG(target_gr >= 10) p_ge_10,
            AVG(target_gr >= 20) p_ge_20, AVG(target_gr >= 50) p_ge_50,
            AVG(target_gr >= 100) p_ge_100 FROM b GROUP BY bucket ORDER BY bucket
        """
        all_rows.append(con.execute(global_q).df())

    all_summary = pd.concat(all_rows, ignore_index=True)
    group_summary = pd.concat(group_rows, ignore_index=True)
    base_p = float(baseline["p_ge_2"])
    top = (all_summary.groupby("feature", as_index=False)
           .agg(avg_p_ge_2=("p_ge_2", "mean"), max_p_ge_2=("p_ge_2", "max"),
                min_p_ge_2=("p_ge_2", "min"), n_buckets=("bucket", "count")))
    top["max_lift_vs_baseline"] = top["max_p_ge_2"] / base_p
    top["min_lift_vs_baseline"] = top["min_p_ge_2"] / base_p
    top["range_p_ge_2"] = top["max_p_ge_2"] - top["min_p_ge_2"]
    top = top.sort_values("range_p_ge_2", ascending=False)

    all_summary.to_csv(a.out / "feature_bucket_summary.csv", index=False)
    group_summary.to_csv(a.out / "feature_window_group_summary.csv", index=False)
    top.to_csv(a.out / "top_features.csv", index=False)
    (a.out / "feature_analysis_summary.json").write_text(
        json.dumps({"baseline": baseline, "n_features": len(features), "n_rows_valid": int(baseline["n"])}, indent=2, default=float),
        encoding="utf-8",
    )

    print(json.dumps({"baseline": baseline, "n_features": len(features), "n_rows_valid": int(baseline["n"])}, indent=2, default=float))
    print(f"Output ditulis ke: {a.out.resolve()}")


if __name__ == "__main__":
    main()
