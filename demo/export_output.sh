#!/usr/bin/env bash
# export_output.sh — Export the latest output CSV from Pachyderm.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$SCRIPT_DIR/data"
pachctl get file block6_write_csv@master:/output.csv -o "$SCRIPT_DIR/data/output_latest.csv"
echo "Exported $SCRIPT_DIR/data/output_latest.csv ($(wc -l < "$SCRIPT_DIR/data/output_latest.csv") lines)"
