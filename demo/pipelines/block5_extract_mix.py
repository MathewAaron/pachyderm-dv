#!/usr/bin/env python3
"""
Block 5 — Extract Data From Popular Mixes
Source: data_helper.extract_data_from_popular_mix()

Input:  /pfs/block4_gen_mixes/mixes.csv
Output: /pfs/out/extracted.csv, /pfs/out/stats.json
"""
import pandas as pd
import json
from datetime import datetime, timezone

df = pd.read_csv("/pfs/block4_gen_mixes/mixes.csv", low_memory=False)
input_rows = len(df)
df_pre = df.copy()

# Extract rows matching Rye-Clover or Wheat-Clover mixes
column_names = ["Rye-Clover-Mix", "Wheat-Clover-Mix"]
valid_columns = [col for col in column_names if col in df.columns]

if not valid_columns:
    raise ValueError("None of the specified mix columns exist in the DataFrame.")

# Keep rows where at least one of the specified columns is 1
df = df[df[valid_columns].eq(1).any(axis=1)]

# Drop columns that contain only NaN values
df = df.dropna(axis=1, how='all')

# Track per-mix hit counts before filtering
per_mix_counts = {col: int(df_pre[col].eq(1).sum()) for col in valid_columns}
columns_before = list(df_pre.columns)

df.to_csv("/pfs/out/extracted.csv", index=False)

# --- quality.json ---
with open("/pfs/out/quality.json", "w") as f:
    json.dump({
        "block": "block5_extract_mix",
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "unique_counts": {col: int(df[col].nunique()) for col in df.columns},
        "row_count": len(df),
        "column_count": len(df.columns),
    }, f, indent=2)

# --- diff.json ---
with open("/pfs/out/diff.json", "w") as f:
    json.dump({
        "block": "block5_extract_mix",
        "rows_in": input_rows,
        "rows_out": len(df),
        "dropped": {
            "no_matching_mix": input_rows - len(df),
        },
        "filter_columns": column_names,
        "per_mix_row_counts": per_mix_counts,
        "columns_dropped_all_nan": [c for c in columns_before if c not in df.columns],
        "retention_pct": round(100 * len(df) / input_rows, 1) if input_rows else 0,
    }, f, indent=2)

with open("/pfs/out/stats.json", "w") as f:
    json.dump({
        "block": "block5_extract_mix",
        "input_rows": input_rows,
        "output_rows": len(df),
        "filter_columns": column_names,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, f, indent=2)

print(f"Block 5 complete: {input_rows} -> {len(df)} rows (filtered to {column_names})")
