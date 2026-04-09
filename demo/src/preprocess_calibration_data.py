#!/usr/bin/env python3

import argparse
import pandas as pd
from from_root import from_here
import sys

sys.path.append(str(from_here('..')))
from utils.utils import *
from data_helper import *
import matplotlib.pyplot as plt

"""
    Generate Mix from Raw data
"""
def parse_args():
    parser = argparse.ArgumentParser(description="Path to CSV.")
    parser.add_argument(
        "--fpath",
        required=True,
        help="Path to the input CSV file.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Read CSV
    raw_data = read_csv_as_df(args.fpath)

    # --- Preprocess raw metadata ---
    raw_data = preprocess_raw_calibration_metadata(raw_data)

    # --- Generate reorder and mix data ---
    mix_data = preprocess_calibration_data(raw_data, ["rgb", "depth"])
    test_duplicate_biomass_fnames(mix_data)
    mix_data = reorder_calibration_metadata(mix_data)

    mix_data = generate_popular_mixes(mix_data) 
    """
        Extracting Mix data
    """
    output_data = extract_data_from_popular_mix(
        mix_metadata=mix_data,
        column_names=["Rye-Clover-Mix", "Wheat-Clover-Mix"],
    )
    output_data = export_results_to_csv(output_data, "output.csv")


if __name__ == "__main__":
    main()