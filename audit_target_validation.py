#!/usr/bin/env python3
"""
Audit dan validasi target untuk dataset sliding-window.

Tujuan script ini:
1. Membaca data ronde mentah dari 410_kalibrasi.md.
2. Membaca hasil feature engineering window dari CSV atau Parquet.
3. Menghubungkan setiap window dengan ronde berikutnya (t+1).
4. Memeriksa window yang tidak memiliki target, duplikasi, dan masalah dasar.
5. Menghasilkan baseline target agar eksperimen fitur berikutnya punya pembanding.

Konsep target yang digunakan:
    window berisi ronde t-N+1 ... t
    fitur dihitung sampai ronde t
    target = gr_result ronde t+1

Script ini TIDAK melakukan prediksi dan TIDAK menyimpulkan adanya signal.
Script ini hanya melakukan audit data dan menyiapkan/validasi target.

Contoh:
    python audit_target_validation.py \
        --raw 410_kalibrasi.md \
        --windows 410_kalibrasi30_31_raw.parquet \
        --out audit_output

Dependensi:
    pip install pandas pyarrow
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


THRESHOLDS = [2, 5, 10, 20, 50, 100]
REQUIRED_RAW_COLUMNS = {"gr_result", "game_id"}
REQUIRED_WINDOW_COLUMNS = {
    "window_size",
    "window_start",
    "window_end",
    "first_game_id",
    "last_game_id",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit data mentah dan target t+1 pada sliding-window dataset."
    )
    parser.add_argument(
        "--raw",
        required=True,
        type=Path,
        help="Path ke data mentah Markdown, misalnya 410_kalibrasi.md.",
    )
    parser.add_argument(
        "--windows",
        required=True,
        type=Path,
        help="Path ke CSV atau Parquet hasil sliding window.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("audit_output"),
        help="Direktori output; default: audit_output.",
    )
    return parser.parse_args()


def read_raw_markdown(path: Path) -> pd.DataFrame:
    """Membaca tabel Markdown dari file 410_kalibrasi.md."""
    text = path.read_text(encoding="utf-8")

    # Ambil baris tabel data. Header dan separator dipertahankan agar pandas
    # dapat membaca tabel dengan cara yang sama seperti tabel Markdown biasa.
    table_lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            table_lines.append(line.strip())

    if len(table_lines) < 3:
        raise ValueError(f"Tidak menemukan tabel Markdown yang valid di {path}")

    # Hilangkan kolom indeks kosong pada format | kol1 | kol2 | ... |
    normalized = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        normalized.append("|" + "|".join(cells) + "|")

    header = normalized[0]
    separator = normalized[1]
    data_lines = normalized[2:]
    csv_like = "\n".join([header, separator, *data_lines])

    # read_csv dengan regex separator lebih toleran terhadap tabel Markdown
    # yang mempunyai spasi di sekitar tanda pipe.
    from io import StringIO

    raw = pd.read_csv(StringIO(csv_like), sep="|", engine="python")
    raw = raw.dropna(axis=1, how="all")
    raw.columns = [str(column).strip() for column in raw.columns]
    raw = raw.dropna(how="all").reset_index(drop=True)

    # Beberapa parser meninggalkan kolom kosong di ujung tabel.
    raw = raw.loc[:, [column for column in raw.columns if column != ""]]

    missing = REQUIRED_RAW_COLUMNS - set(raw.columns)
    if missing:
        raise ValueError(f"Kolom raw tidak lengkap, hilang: {sorted(missing)}")

    # Baris separator Markdown kadang terbaca sebagai data.
    raw = raw[~raw["game_id"].astype(str).str.fullmatch(r"-+")]
    raw["game_id"] = pd.to_numeric(raw["game_id"], errors="coerce")
    raw["gr_result"] = pd.to_numeric(raw["gr_result"], errors="coerce")
    raw = raw.dropna(subset=["game_id", "gr_result"]).copy()
    raw["game_id"] = raw["game_id"].astype("int64")
    raw["raw_order"] = range(len(raw))

    return raw


def read_windows(path: Path) -> pd.DataFrame:
    """Membaca dataset window dari CSV atau Parquet."""
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        windows = pd.read_parquet(path)
    elif suffix == ".csv":
        windows = pd.read_csv(path)
    else:
        raise ValueError("File windows harus berekstensi .csv atau .parquet")

    windows.columns = [str(column).strip() for column in windows.columns]
    missing = REQUIRED_WINDOW_COLUMNS - set(windows.columns)
    if missing:
        raise ValueError(
            f"Kolom window tidak lengkap, hilang: {sorted(missing)}"
        )

    for column in [
        "window_size",
        "window_start",
        "window_end",
        "first_game_id",
        "last_game_id",
    ]:
        windows[column] = pd.to_numeric(windows[column], errors="coerce")

    return windows


def add_targets(raw: pd.DataFrame, windows: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Tambahkan target t+1 berdasarkan posisi last_game_id di data raw."""
    raw_by_game = raw.drop_duplicates("game_id").set_index("game_id")
    ordered_game_ids = raw["game_id"].tolist()
    next_game_by_game = {
        ordered_game_ids[index]: ordered_game_ids[index + 1]
        for index in range(len(ordered_game_ids) - 1)
    }

    result = windows.copy()
    result["target_game_id"] = result["last_game_id"].map(next_game_by_game)
    result["target_gr"] = result["target_game_id"].map(raw_by_game["gr_result"])

    # Target tidak boleh sama dengan game terakhir di window.
    result["target_is_same_as_last"] = (
        result["target_game_id"] == result["last_game_id"]
    )

    # Cek sederhana apakah game pertama/terakhir window memang ada di raw.
    raw_game_ids = set(raw["game_id"])
    result["first_game_exists"] = result["first_game_id"].isin(raw_game_ids)
    result["last_game_exists"] = result["last_game_id"].isin(raw_game_ids)

    # Target binary/range untuk baseline dan eksperimen berikutnya.
    result["target_low"] = result["target_gr"] < 2
    for threshold in THRESHOLDS:
        result[f"target_ge_{threshold}"] = result["target_gr"] >= threshold

    summary: dict[str, Any] = {
        "raw_rounds": int(len(raw)),
        "window_rows": int(len(result)),
        "missing_target_rows": int(result["target_gr"].isna().sum()),
        "target_same_as_last_rows": int(result["target_is_same_as_last"].sum()),
        "first_game_missing_rows": int((~result["first_game_exists"]).sum()),
        "last_game_missing_rows": int((~result["last_game_exists"]).sum()),
        "duplicate_window_rows": int(
            result.duplicated(
                subset=["window_size", "window_start", "window_end"]
            ).sum()
        ),
    }
    return result, summary


def make_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Buat baseline target global dan per window_size."""
    rows: list[dict[str, Any]] = []
    grouping = [("ALL", df)]
    grouping.extend((str(size), group) for size, group in df.groupby("window_size"))

    for group_name, group in grouping:
        valid = group.dropna(subset=["target_gr"])
        row: dict[str, Any] = {
            "window_group": group_name,
            "n_total": int(len(group)),
            "n_valid_target": int(len(valid)),
            "low_rate": float(valid["target_low"].mean()) if len(valid) else None,
        }
        for threshold in THRESHOLDS:
            column = f"target_ge_{threshold}"
            row[f"p_ge_{threshold}"] = (
                float(valid[column].mean()) if len(valid) else None
            )
        rows.append(row)

    return pd.DataFrame(rows)


def make_period_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Membandingkan baseline berdasarkan urutan window_end."""
    valid = df.dropna(subset=["target_gr"]).copy()
    if valid.empty:
        return pd.DataFrame()

    valid["period"] = pd.qcut(
        valid["window_end"], q=3, labels=["early", "middle", "late"], duplicates="drop"
    )
    rows = []
    for period, group in valid.groupby("period", observed=True):
        row: dict[str, Any] = {"period": str(period), "n": int(len(group))}
        row["low_rate"] = float(group["target_low"].mean())
        for threshold in THRESHOLDS:
            row[f"p_ge_{threshold}"] = float(group[f"target_ge_{threshold}"].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def json_safe(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    raw = read_raw_markdown(args.raw)
    windows = read_windows(args.windows)
    audited, target_summary = add_targets(raw, windows)

    raw_schema = pd.DataFrame(
        {
            "column": raw.columns,
            "dtype": [str(dtype) for dtype in raw.dtypes],
            "null_count": [int(raw[column].isna().sum()) for column in raw.columns],
        }
    )
    window_sizes = (
        audited["window_size"].dropna().astype(int).value_counts().sort_index()
    )
    rows_by_window_size = window_sizes.rename("rows").reset_index(names="window_size")

    summary: dict[str, Any] = {
        "raw_file": str(args.raw),
        "windows_file": str(args.windows),
        "raw_columns": list(raw.columns),
        "window_columns": list(windows.columns),
        "window_size_min": json_safe(audited["window_size"].min()),
        "window_size_max": json_safe(audited["window_size"].max()),
        "n_window_sizes": int(audited["window_size"].nunique()),
        "window_end_min": json_safe(audited["window_end"].min()),
        "window_end_max": json_safe(audited["window_end"].max()),
        **target_summary,
    }

    audited.to_csv(args.out / "audited_windows_with_targets.csv", index=False)
    raw_schema.to_csv(args.out / "raw_schema.csv", index=False)
    rows_by_window_size.to_csv(args.out / "rows_by_window_size.csv", index=False)
    make_baseline(audited).to_csv(args.out / "baseline.csv", index=False)
    make_period_summary(audited).to_csv(args.out / "period_summary.csv", index=False)
    (args.out / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nOutput ditulis ke: {args.out.resolve()}")
    print("File utama yang perlu dikirim kembali:")
    print("  - audit_summary.json")
    print("  - baseline.csv")
    print("  - period_summary.csv")
    print("  - rows_by_window_size.csv")


if __name__ == "__main__":
    main()
