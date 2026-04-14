#!/usr/bin/env python3
"""
Block 6 — Export Final Results to CSV
Source: data_helper.export_results_to_csv()

Input:  /pfs/block5_extract_mix/extracted.csv
Output: /pfs/out/output.csv, /pfs/out/stats.json
"""
import pandas as pd
import json
from datetime import datetime, timezone

df = pd.read_csv("/pfs/block5_extract_mix/extracted.csv", low_memory=False)
input_rows = len(df)
columns_before = list(df.columns)

# Drop all-NaN columns
df = df.dropna(axis=1, how='all')
columns_dropped = [c for c in columns_before if c not in df.columns]

# Write final output
df.to_csv("/pfs/out/output.csv", index=False)

# --- quality.json ---
with open("/pfs/out/quality.json", "w") as f:
    json.dump({
        "block": "block6_write_csv",
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "unique_counts": {col: int(df[col].nunique()) for col in df.columns},
        "row_count": len(df),
        "column_count": len(df.columns),
    }, f, indent=2)

# --- diff.json ---
with open("/pfs/out/diff.json", "w") as f:
    json.dump({
        "block": "block6_write_csv",
        "rows_in": input_rows,
        "rows_out": len(df),
        "columns_dropped_all_nan": columns_dropped,
        "final_columns": list(df.columns),
        "retention_pct": round(100 * len(df) / input_rows, 1) if input_rows else 0,
    }, f, indent=2)

with open("/pfs/out/stats.json", "w") as f:
    json.dump({
        "block": "block6_write_csv",
        "input_rows": input_rows,
        "output_rows": len(df),
        "columns": list(df.columns),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, f, indent=2)

print(df)
print(f"\nBlock 6 complete: {len(df)} rows, {len(df.columns)} columns -> output.csv")
