#!/usr/bin/env python3
"""
Block 3 — Reorder / Pivot Calibration Metadata
Source: data_helper.reorder_calibration_metadata()

Input:  /pfs/block2_clean_filter/cleaned.csv
Output: /pfs/out/pivoted.csv, /pfs/out/stats.json
"""
import pandas as pd
import json
from datetime import datetime, timezone

df = pd.read_csv("/pfs/block2_clean_filter/cleaned.csv", low_memory=False)
input_rows = len(df)

# Pivot: rows per (FileName × ImageType), columns per Species, values = BiomassWeight
df_pivot = df.pivot_table(
    index=['FileName', 'ImageUrl', 'SetId', 'ImageType', 'GroundFrameDist', 'TypeOfCoverCrops'],
    columns='Species',
    values='BiomassWeight',
    aggfunc='first'
)
df_pivot = df_pivot.reset_index()
df_pivot = df_pivot.rename_axis(None, axis=1)

df_pivot.to_csv("/pfs/out/pivoted.csv", index=False)

# --- quality.json ---
with open("/pfs/out/quality.json", "w") as f:
    json.dump({
        "block": "block3_reorder_pivot",
        "null_counts": df_pivot.isnull().sum().to_dict(),
        "dtypes": df_pivot.dtypes.astype(str).to_dict(),
        "unique_counts": {col: int(df_pivot[col].nunique()) for col in df_pivot.columns},
        "row_count": len(df_pivot),
        "column_count": len(df_pivot.columns),
    }, f, indent=2)

# --- diff.json ---
with open("/pfs/out/diff.json", "w") as f:
    json.dump({
        "block": "block3_reorder_pivot",
        "rows_in": input_rows,
        "rows_out": len(df_pivot),
        "operation": "pivot_table",
        "index_columns": ["FileName", "ImageUrl", "SetId", "ImageType", "GroundFrameDist", "TypeOfCoverCrops"],
        "pivot_column": "Species",
        "value_column": "BiomassWeight",
        "species_columns_created": [c for c in df_pivot.columns if c not in ["FileName", "ImageUrl", "SetId", "ImageType", "GroundFrameDist", "TypeOfCoverCrops"]],
        "compression_ratio": round(input_rows / len(df_pivot), 2) if len(df_pivot) else 0,
    }, f, indent=2)

with open("/pfs/out/stats.json", "w") as f:
    json.dump({
        "block": "block3_reorder_pivot",
        "input_rows": input_rows,
        "output_rows": len(df_pivot),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, f, indent=2)

print(f"Block 3 complete: {input_rows} -> {len(df_pivot)} rows (pivoted)")
