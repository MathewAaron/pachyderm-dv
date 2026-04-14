#!/usr/bin/env bash
# cleanup.sh — Delete all demo pipelines, repos, and local exported data.
set -eu

echo "Deleting pipelines..."
for p in block6_write_csv block5_extract_mix block4_gen_mixes \
         block3_reorder_pivot block2_clean_filter block1_preprocess; do
  pachctl delete pipeline "$p" 2>/dev/null && echo "  deleted $p" || echo "  $p not found, skipping"
done

echo "Deleting input repo..."
pachctl delete repo pm3d_data 2>/dev/null && echo "  deleted pm3d_data" || echo "  pm3d_data not found, skipping"

echo "Removing local exported files..."
rm -rf data/output_latest.csv data/diagnostics data/intermediate

echo "Cleanup complete."
