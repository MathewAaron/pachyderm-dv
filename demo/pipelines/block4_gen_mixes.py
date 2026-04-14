#!/usr/bin/env python3
"""
Block 4 — Generate Popular Mix Flag Columns
Source: data_helper.generate_popular_mixes()

Input:  /pfs/block3_reorder_pivot/pivoted.csv
Output: /pfs/out/mixes.csv, /pfs/out/stats.json
"""
import pandas as pd
import json
from datetime import datetime, timezone

df = pd.read_csv("/pfs/block3_reorder_pivot/pivoted.csv", low_memory=False)
input_rows = len(df)

# Define all 16 mix combinations
mix_defs = {
    'Rye-Vetch-Mix': ['Cereal rye', 'Hairy vetch'],
    'Rye-Clover-Mix': ['Cereal rye', 'Crimson clover'],
    'Rye-Peas-Mix': ['Cereal rye', 'Winter peas'],
    'Rye-Vetch-Brassica-Mix': ['Cereal rye', 'Hairy vetch', 'Brassica napus'],
    'Rye-Clover-Brassica-Mix': ['Cereal rye', 'Crimson clover', 'Brassica napus'],
    'Rye-Peas-Brassica-Mix': ['Cereal rye', 'Winter peas', 'Brassica napus'],
    'Wheat-Vetch-Mix': ['Wheat', 'Hairy vetch'],
    'Wheat-Clover-Mix': ['Wheat', 'Crimson clover'],
    'Wheat-Peas-Mix': ['Wheat', 'Winter peas'],
    'Wheat-Vetch-Brassica-Mix': ['Wheat', 'Hairy vetch', 'Brassica napus'],
    'Wheat-Clover-Brassica-Mix': ['Wheat', 'Crimson clover', 'Brassica napus'],
    'Wheat-Peas-Brassica-Mix': ['Wheat', 'Winter peas', 'Brassica napus'],
    'Rye-Mix': ['Cereal rye'],
    'Wheat-Mix': ['Wheat'],
    'Rye-Brassica-Mix': ['Cereal rye', 'Brassica napus'],
    'Wheat-Brassica-Mix': ['Wheat', 'Brassica napus'],
}

for mix_name, species_list in mix_defs.items():
    # Flag = 1 if all required species columns are non-null for that row
    df[mix_name] = df.apply(
        lambda row, sp=species_list: 1 if all(pd.notna(row.get(s)) for s in sp) else None,
        axis=1
    )

df.to_csv("/pfs/out/mixes.csv", index=False)

# --- quality.json ---
mix_hit_counts = {name: int(df[name].eq(1).sum()) for name in mix_defs}
with open("/pfs/out/quality.json", "w") as f:
    json.dump({
        "block": "block4_gen_mixes",
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "unique_counts": {col: int(df[col].nunique()) for col in df.columns},
        "row_count": len(df),
        "column_count": len(df.columns),
    }, f, indent=2)

# --- diff.json ---
with open("/pfs/out/diff.json", "w") as f:
    json.dump({
        "block": "block4_gen_mixes",
        "rows_in": input_rows,
        "rows_out": len(df),
        "operation": "add_mix_flags",
        "columns_added": list(mix_defs.keys()),
        "mix_hit_counts": mix_hit_counts,
        "rows_matching_any_mix": int(df[list(mix_defs.keys())].eq(1).any(axis=1).sum()),
        "rows_matching_no_mix": int((~df[list(mix_defs.keys())].eq(1).any(axis=1)).sum()),
    }, f, indent=2)

with open("/pfs/out/stats.json", "w") as f:
    json.dump({
        "block": "block4_gen_mixes",
        "input_rows": input_rows,
        "output_rows": len(df),
        "mix_columns_added": list(mix_defs.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, f, indent=2)

print(f"Block 4 complete: {input_rows} rows, added {len(mix_defs)} mix columns")
