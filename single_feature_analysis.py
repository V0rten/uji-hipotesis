#!/usr/bin/env python3
"""
Single-feature analysis untuk dataset sliding-window.

Tujuan script ini:
1. Membaca dataset window yang sudah punya target `t+1` OR membuat target dari raw + windows.
2. Mengevaluasi setiap fitur terhadap target utama, misalnya `target_ge_2`.
3. Mengukur apakah fitur punya lift yang konsisten vs baseline global.
4. Mengelompokkan hasil berdasarkan ukuran window agar tidak terlalu bias karena overlap.
5. Menghasilkan ringkasan yang mudah dikirim kembali untuk interpretasi.

Fungsi utama:
    - fitur numerik -> membagi ke beberapa bucket (qcut) lalu menghitung p(target)
    - fitur boolean / count -> evaluasi per nilai 0/1 atau threshold tertentu
    - output ringkas per fitur dan per kelompok ukuran window

Contoh pemakaian:
    python single_feature_analysis.py \
        --data audited_windows_with_targets.csv \
        --out feature_analysis

    atau jika dataset belum punya target:
    python single_feature_analysis.py \
        --raw 410_kalibrasi.md \
        --windows 410_kalibrasi10_2000_raw.parquet \
        --out feature_analysis

Catatan penting:
    - Data window sangat overlap. Jangan langsung menganggap semua baris sebagai sample independen.
    - Saat interpretasi, fokus pada signal yang konsisten lintas window_size.
    - Output ringkas yang perlu dikirim kembali: feature_window_group_summary.csv dan top_features.csv.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

TARGET_FIELDS = ["target_gr", "target_low"]
THRESHOLDS = [2, 5, 10, 20, 50, 100]
TARGET_COLUMNS = [f"target_ge_{threshold}" for threshold in THRESHOLDS]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analisis fitur tunggal untuk dataset window dengan target t+1."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path dataset window yang sudah memiliki target (CSV/Parquet).",
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=None,
        help="Path ke raw markdown (opsional, dipakai hanya jika --data tidak ada).",
    )
    parser.add_argument(
        "--windows",
        type=Path,
        default=None,
        help="Path ke window dataset (CSV/Parquet), hanya untuk membangun target jika --data tidak ada.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("feature_analysis"),
        help="Direktori output; default: feature_analysis.",
    )
    return parser.parse_args()


def read_raw_markdown(path: Path) -> pd.DataFrame:
    """Baca file 410_kalibrasi.md seperti pada script audit sebelumnya."""
    text = path.read_text(encoding="utf-8")
    table_lines = [line.strip() for line in text.splitlines() if line.lstrip().startswith("|")]
    if len(table_lines) < 3:
        raise ValueError(f"Tidak menemukan tabel Markdown valid di {path}")

    from io import StringIO

    normalized = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        normalized.append("|" + "|".join(cells) + "|")

    csv_like = "\n".join(normalized)
    raw = pd.read_csv(StringIO(csv_like), sep="|", engine="python")
    raw = raw.dropna(axis=1, how="all").reset_index(drop=True)
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.loc[:, [c for c in raw.columns if c != ""]].copy()

    if "game_id" not in raw.columns or "gr_result" not in raw.columns:
        raise ValueError("Raw data harus punya kolom 'game_id' dan 'gr_result'.")

    raw["game_id"] = pd.to_numeric(raw["game_id"], errors="coerce")
    raw["gr_result"] = pd.to_numeric(raw["gr_result"], errors="coerce")
    raw = raw.dropna(subset=["game_id", "gr_result"]).copy()
    raw["game_id"] = raw["game_id"].astype("int64")
    raw = raw.drop_duplicates(subset=["game_id"], keep="last").sort_values("game_id").reset_index(drop=True)
    return raw


def read_windows(path: Path) -> pd.DataFrame:
    """Baca file window dari CSV atau Parquet."""
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df = pd.read_parquet(path)
    elif suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError("File windows harus .csv atau .parquet")

    df.columns = [str(c).strip() for c in df.columns]
    for c in ["window_size", "window_start", "window_end", "first_game_id", "last_game_id"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def build_target_frame(raw: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    """Membuat target t+1 untuk setiap row window."""
    result = windows.copy()
    raw_index = raw.drop_duplicates("game_id").set_index("game_id")

    # target_game_id = game yang menjadi ronde setelah window
    game_to_next = {}
    ordered = raw["game_id"].astype(int).tolist()
    for i in range(len(ordered) - 1):
        game_to_next[ordered[i]] = ordered[i + 1]

    result["target_game_id"] = result["last_game_id"].map(game_to_next)
    result["target_gr"] = result["target_game_id"].map(raw_index["gr_result"])

    # Pastikan target tidak berisi data dari window itu sendiri
    result["target_is_same_as_last"] = result["target_game_id"] == result["last_game_id"]
    result["target_low"] = result["target_gr"] < 2
    for threshold in THRESHOLDS:
        result[f"target_ge_{threshold}"] = result["target_gr"] >= threshold

    # Hapus row tanpa target pada akhir dataset (normal untuk window terbesar)
    result = result.dropna(subset=["target_gr"]).reset_index(drop=True)
    return result


def candidate_features(df: pd.DataFrame) -> list[str]:
    """Pilih fitur kandidat yang layak diukur. Target columns dan ID metadata dikeluarkan."""
    exclude = {
        "window_no",
        "window_start",
        "window_end",
        "window_size",
        "first_game_id",
        "last_game_id",
        "first_tag_ts",
        "last_ts_gr",
        "first_tag_ts_iso",
        "target_game_id",
        "target_gr",
        "target_low",
        "raw_order",
    }
    exclude |= {f"target_ge_{t}" for t in THRESHOLDS}
    exclude |= {"target_is_same_as_last"}

    columns = []
    for col in df.columns:
        if col in exclude:
            continue
        if col.startswith("target_"):
            continue
        if col.startswith("first_") and col not in {"first_game_id", "first_tag_ts", "first_tag_ts_iso"}:
            # tetap boleh dipakai jika memang feature; tapi yang umum di window sudah masuk daftar.
            pass
        columns.append(col)

    # Hapus feature kolom yang identik dengan target (jika punya)
    safe = []
    for col in columns:
        if col in {"last_gr", "max_gr", "mean_gr", "min_gr"}:
            safe.append(col)
        elif df[col].nunique(dropna=True) > 1:
            safe.append(col)
    return safe


def safe_bucket_numeric(series: pd.Series, n_bins: int = 5) -> pd.Series:
    """Buat bucket numerik dengan guard jika nilai terlalu sedikit atau semua sama."""
    s = series.dropna()
    if s.empty:
        return pd.Series(pd.NA, index=series.index, dtype="object")

    if s.nunique() <= 1:
        return s.astype(str)

    try:
        bins = pd.qcut(s, q=min(n_bins, s.nunique()), duplicates="drop")
        return pd.Series(bins.astype(str), index=s.index)
    except Exception:
        ordered = s.sort_values().unique()
        labels = []
        for val in s:
            labels.append(str(val))
        return pd.Series(labels, index=s.index)


def make_bucket_summary(df: pd.DataFrame, feature: str) -> pd.DataFrame:
    """Ringkas satu fitur menjadi bucket per nilai / quantile."""
    series = df[feature]
    if pd.api.types.is_bool_dtype(series) or series.nunique(dropna=True) <= 2:
        # fitur boolean / binary
        out = series.to_frame(name=feature).copy()
        out["bucket"] = out[feature].astype(str)
    else:
        # numerik -> qcut
        out = pd.DataFrame({feature: series})
        out["bucket"] = safe_bucket_numeric(out[feature], n_bins=5)

    merged = pd.concat([df[["target_low"] + [f"target_ge_{t}" for t in THRESHOLDS]], out], axis=1)
    merged = merged.dropna(subset=["bucket"]).copy()

    rows = []
    for bucket, group in merged.groupby("bucket", dropna=True):
        n = len(group)
        row = {
            "feature": feature,
            "bucket": str(bucket),
            "n": int(n),
            "low_rate": float(group["target_low"].mean()),
        }
        for threshold in THRESHOLDS:
            col = f"target_ge_{threshold}"
            row[f"p_ge_{threshold}"] = float(group[col].mean())
        rows.append(row)

    return pd.DataFrame(rows)


def summarize_by_window_group(df: pd.DataFrame, feature: str) -> pd.DataFrame:
    """Agregasi stabilitas fitur per kelompok ukuran window."""
    data = df[["window_size", feature, "target_low"] + [f"target_ge_{t}" for t in THRESHOLDS]].copy()
    data["window_group"] = pd.cut(
        data["window_size"],
        bins=[0, 10, 30, 50, 100, 250, 500, 1000, 2000, 999999],
        labels=["<=10", "11-30", "31-50", "51-100", "101-250", "251-500", "501-1000", "1001-2000", ">2000"],
        right=False,
        include_lowest=True,
    )

    rows = []
    for group_name, group in data.groupby("window_group", dropna=False):
        if len(group) == 0:
            continue
        feature_values = group[feature].dropna()
        if feature_values.empty:
            continue

        # Jika feature numerik, bucket menurut quantile untuk mengurangi outlier effect
        local = group.copy()
        if pd.api.types.is_numeric_dtype(local[feature]):
            local["bucket"] = safe_bucket_numeric(local[feature], n_bins=5)
        else:
            local["bucket"] = local[feature].astype(str)

        for bucket, sub in local.groupby("bucket", dropna=True):
            row = {
                "feature": feature,
                "window_group": str(group_name),
                "bucket": str(bucket),
                "n": int(len(sub)),
                "low_rate": float(sub["target_low"].mean()),
            }
            for threshold in THRESHOLDS:
                row[f"p_ge_{threshold}"] = float(sub[f"target_ge_{threshold}"].mean())
            rows.append(row)

    return pd.DataFrame(rows)


def compute_top_features(summary: pd.DataFrame, baseline: dict[str, float]) -> pd.DataFrame:
    """Urutkan fitur berdasarkan kekuatan lift relatif terhadap baseline."""
    out_rows = []
    for feature in sorted(summary["feature"].unique()):
        subset = summary[summary["feature"] == feature].copy()
        if subset.empty:
            continue

        # Main metric: p_ge_2 relative to baseline global
        base = baseline["p_ge_2"]
        lift_values = []
        for _, row in subset.iterrows():
            p = row.get("p_ge_2")
            if pd.notna(p):
                lift_values.append(float(p / base) if base else 1.0)

        if not lift_values:
            continue

        out_rows.append(
            {
                "feature": feature,
                "avg_p_ge_2": float(subset["p_ge_2"].mean()),
                "max_p_ge_2": float(subset["p_ge_2"].max()),
                "avg_lift_vs_baseline": float(sum(lift_values) / len(lift_values)),
                "max_lift_vs_baseline": float(max(lift_values)),
                "n_buckets": int(len(subset)),
            }
        )

    top = pd.DataFrame(out_rows).sort_values(
        ["avg_lift_vs_baseline", "max_lift_vs_baseline"],
        ascending=False,
    )
    return top.reset_index(drop=True)


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.data is not None:
        data_path = args.data
        df = pd.read_parquet(data_path) if data_path.suffix.lower() == ".parquet" else pd.read_csv(data_path)
    elif args.raw is not None and args.windows is not None:
        raw = read_raw_markdown(args.raw)
        windows = read_windows(args.windows)
        df = build_target_frame(raw, windows)
    else:
        raise ValueError("Harus sediakan --data ATAU --raw + --windows")

    df.columns = [str(c).strip() for c in df.columns]
    required = ["target_low"] + [f"target_ge_{t}" for t in THRESHOLDS]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset tidak punya target yang dibutuhkan. Kolom hilang: {missing}")

    baseline = {
        "p_ge_2": float(df["target_ge_2"].mean()),
        "p_ge_5": float(df["target_ge_5"].mean()),
        "p_ge_10": float(df["target_ge_10"].mean()),
        "p_ge_20": float(df["target_ge_20"].mean()),
        "p_ge_50": float(df["target_ge_50"].mean()),
        "p_ge_100": float(df["target_ge_100"].mean()),
    }

    feature_list = candidate_features(df)
    bucket_summaries = []
    by_window_group = []

    for feat in feature_list:
        if feat not in df.columns:
            continue
        if df[feat].isna().all():
            continue

        feature_bucket = make_bucket_summary(df, feat)
        bucket_summaries.append(feature_bucket)

        by_window = summarize_by_window_group(df, feat)
        by_window_group.append(by_window)

    if not bucket_summaries:
        raise ValueError("Tidak ada fitur yang valid untuk dianalisis.")

    feature_summary = pd.concat(bucket_summaries, ignore_index=True)
    window_group_summary = pd.concat(by_window_group, ignore_index=True)
    top_features = compute_top_features(feature_summary, baseline)

    feature_summary.to_csv(args.out / "feature_bucket_summary.csv", index=False)
    window_group_summary.to_csv(args.out / "feature_window_group_summary.csv", index=False)
    top_features.to_csv(args.out / "top_features.csv", index=False)

    summary = {
        "baseline": baseline,
        "n_total_rows": int(len(df)),
        "n_features": int(len(feature_list)),
        "top_features": top_features.head(20).to_dict(orient="records"),
    }
    (args.out / "feature_analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps({
        "n_total_rows": int(len(df)),
        "n_features": int(len(feature_list)),
        "baseline": baseline,
    }, indent=2, ensure_ascii=False))
    print(f"\nOutput ditulis di: {args.out.resolve()}")
    print("File utama:")
    print("  - feature_bucket_summary.csv")
    print("  - feature_window_group_summary.csv")
    print("  - top_features.csv")
    print("  - feature_analysis_summary.json")


if __name__ == "__main__":
    main()
