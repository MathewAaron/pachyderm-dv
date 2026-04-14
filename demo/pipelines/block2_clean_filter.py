#!/usr/bin/env python3
"""
Block 2 — Clean and Filter Calibration Data
Source: data_helper.preprocess_calibration_data() + data_helper.test_duplicate_biomass_fnames()

Input:  /pfs/block1_preprocess/preprocessed.csv
Output: /pfs/out/cleaned.csv, /pfs/out/stats.json
"""
import pandas as pd
import json
from datetime import datetime, timezone

df = pd.read_csv("/pfs/block1_preprocess/preprocessed.csv", low_memory=False)
input_rows = len(df)
diff_steps = {}

# Convert BiomassWeight to numeric
df['BiomassWeight'] = pd.to_numeric(df['BiomassWeight'], errors='coerce')

# Drop rows missing essential fields
before = len(df)
df = df.dropna(subset=['ImgName(app)', 'Species', 'FileName', 'ImageUrl', 'GroundFrameDist'])
diff_steps['missing_essential_fields'] = before - len(df)

# Fix species naming errors
df['Species'] = df['Species'].replace({
    '0.0': 'Other', '0': 'Other', 'OTHER': 'Other',
    'Pea': 'Peas', 'Crimnson clover': 'Crimson clover'
})

# Drop duplicates by (FileName, Species)
before = len(df)
df = df.drop_duplicates(subset=['FileName', 'Species'])
diff_steps['duplicate_filename_species'] = before - len(df)

# Filter to rgb and depth images only
before = len(df)
df = df[df['ImageType'].isin(['rgb', 'depth'])]
diff_steps['non_rgb_depth_images'] = before - len(df)

# Sort
df = df.sort_values(['FileName', 'Species'], ascending=True)

# Sanity check: no duplicate (FileName, ImageType, Species) entries
suspicious = (
    df.groupby(['FileName', 'ImageType', 'Species'])
    .size()
    .reset_index(name='count')
)
suspicious = suspicious[suspicious['count'] > 1]
assert len(suspicious) == 0, f"Duplicate entries found: {suspicious}"

df.to_csv("/pfs/out/cleaned.csv", index=False)

# --- quality.json ---
with open("/pfs/out/quality.json", "w") as f:
    json.dump({
        "block": "block2_clean_filter",
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "unique_counts": {col: int(df[col].nunique()) for col in df.columns},
        "row_count": len(df),
        "column_count": len(df.columns),
    }, f, indent=2)

# --- diff.json ---
diff_steps['total_dropped'] = input_rows - len(df)
with open("/pfs/out/diff.json", "w") as f:
    json.dump({
        "block": "block2_clean_filter",
        "rows_in": input_rows,
        "rows_out": len(df),
        "dropped": diff_steps,
        "retention_pct": round(100 * len(df) / input_rows, 1) if input_rows else 0,
    }, f, indent=2)

with open("/pfs/out/stats.json", "w") as f:
    json.dump({
        "block": "block2_clean_filter",
        "input_rows": input_rows,
        "output_rows": len(df),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, f, indent=2)

print(f"Block 2 complete: {input_rows} -> {len(df)} rows")
