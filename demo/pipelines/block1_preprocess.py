#!/usr/bin/env python3
"""
Block 1 — Preprocess Raw Calibration Metadata
Source: data_helper.preprocess_raw_calibration_metadata()

Input:  /pfs/pm3d_data/*.csv
Output: /pfs/out/preprocessed.csv, /pfs/out/stats.json
"""
import pandas as pd
import json
import glob
import os
from datetime import datetime, timezone

csv_files = sorted(glob.glob("/pfs/pm3d_data/*.csv"), key=lambda f: -os.path.getsize(f))
if not csv_files:
    raise FileNotFoundError("No CSV file found in /pfs/pm3d_data/")
df = pd.read_csv(csv_files[0], low_memory=False)
input_rows = len(df)

# Rename columns to standardized names
df = df.rename(columns={
    'image_image_url': 'ImageUrl',
    'image_image_type': 'ImageType',
    'set_distance': 'GroundFrameDist',
    'type_of_crop': 'TypeOfCrop',
    'type_of_cover_crops': 'TypeOfCoverCrops',
    'Dry Weight (g)': 'BiomassWeight',
    'Image Name (from PlantMap3D app)': 'ImgName(app)',
    'set_set_number': 'SetId'
})

# Extract filename from URL
df['FileName'] = df['ImageUrl'].str.split('/').str[-1]

# Drop first data row (index 0) — duplicate header in source CSV
df = df.drop(index=0).reset_index(drop=True)

# Drop unnamed index column if present
if 'Unnamed: 0' in df.columns:
    df = df.drop('Unnamed: 0', axis=1)

# Strip whitespace from column names
df.columns = [col.strip() for col in df.columns]

# Fill missing Species with 'Other' where Functional Group is 'Other'
mask = (df["Functional Group"] == "Other") & (df["Species"].isna())
df.loc[mask, "Species"] = "Other"

df.to_csv("/pfs/out/preprocessed.csv", index=False)

# --- quality.json: column-level diagnostics ---
with open("/pfs/out/quality.json", "w") as f:
    json.dump({
        "block": "block1_preprocess",
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "unique_counts": {col: int(df[col].nunique()) for col in df.columns},
        "row_count": len(df),
        "column_count": len(df.columns),
    }, f, indent=2)

# --- diff.json: what changed ---
with open("/pfs/out/diff.json", "w") as f:
    json.dump({
        "block": "block1_preprocess",
        "rows_in": input_rows,
        "rows_out": len(df),
        "dropped": {
            "duplicate_header_row": 1,
            "species_filled_as_other": int(mask.sum()),
        },
        "columns_removed": ["Unnamed: 0"] if 'Unnamed: 0' not in df.columns else [],
        "retention_pct": round(100 * len(df) / input_rows, 1) if input_rows else 0,
    }, f, indent=2)

with open("/pfs/out/stats.json", "w") as f:
    json.dump({
        "block": "block1_preprocess",
        "input_rows": input_rows,
        "output_rows": len(df),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, f, indent=2)

print(f"Block 1 complete: {input_rows} -> {len(df)} rows")
