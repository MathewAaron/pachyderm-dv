#!/usr/bin/env bash
# startup.sh — Create the input repo, upload data, and deploy all pipelines.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_FILE="${1:-$SCRIPT_DIR/data/pm3d_data_partial.csv}"

if [ ! -f "$DATA_FILE" ]; then
  echo "ERROR: Data file not found: $DATA_FILE"
  echo "Usage: sh startup.sh [path/to/data.csv]"
  exit 1
fi

echo "Creating input repo..."
pachctl create repo pm3d_data

# echo "Uploading $DATA_FILE ..."
# pachctl put file pm3d_data@master:/pm3d_data.csv -f "$DATA_FILE"

echo "Deploying pipelines..."
for spec in "$SCRIPT_DIR"/specs/block1_preprocess.json "$SCRIPT_DIR"/specs/block2_clean_filter.json \
            "$SCRIPT_DIR"/specs/block3_reorder_pivot.json "$SCRIPT_DIR"/specs/block4_gen_mixes.json \
            "$SCRIPT_DIR"/specs/block5_extract_mix.json "$SCRIPT_DIR"/specs/block6_write_csv.json; do
  pachctl create pipeline -f "$spec" && echo "  created $spec" || echo "  FAILED: $spec"
done

echo ""
echo "All pipelines deployed. Monitor the cascade with:"
echo "  pachctl list pipeline"
echo "  pachctl list job"
echo ""
echo "When all pipelines show 'success', export the result with:"
echo "  sh export_output.sh"
