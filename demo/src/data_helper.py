#!/usr/bin/env python3

import pandas as pd
from from_root import from_here
import os, sys
sys.path.append(str(from_here('..')))
from utils.utils import *

def preprocess_raw_calibration_metadata(raw_calibration_data: pd.DataFrame) -> pd.DataFrame:
    """
        Standardize and clean raw calibration metadata before preprocessing.
    """
    metadata = raw_calibration_data.copy()

    metadata = metadata.rename(columns={
        'image_image_url': 'ImageUrl',
        'image_image_type': 'ImageType',
        'set_distance': 'GroundFrameDist',
        'type_of_crop': 'TypeOfCrop',
        'type_of_cover_crops': 'TypeOfCoverCrops',
        'Dry Weight (g)': 'BiomassWeight',
        'Image Name (from PlantMap3D app)': 'ImgName(app)',
        'set_set_number': 'SetId'
    })

    metadata['FileName'] = metadata['ImageUrl'].str.split('/').str[-1]
    metadata = metadata.drop(index=0).reset_index(drop=True)
    metadata = metadata.drop('Unnamed: 0', axis=1)

    # Strip whitespace from column names
    metadata.columns = [col.strip() for col in metadata.columns]

    # Fill missing 'Other' in Species wherever Functional Group has 'Other'
    mask = (metadata["Functional Group"] == "Other") & (metadata["Species"].isna())
    metadata.loc[mask, "Species"] = "Other"

    return metadata

def preprocess_calibration_data(calibration_metadata,img_type_list:list = None):
    """
        img_type : is a list of image types ['rgb'],['rgb','depth','right', 'left']

        NOTE : This function cleans the metadata, standardizes inputs and is a helper function for the reordering function
    """
    # merge columns DryWeight(g) and DryWt(g)
    # calibration_metadata['BiomassWeight'] = calibration_metadata['DryWeight(g)'].combine_first(calibration_metadata['DryWt(g)'])
    # calibration_metadata = calibration_metadata.drop(columns=['DryWeight(g)','DryWt(g)'])
    calibration_metadata['BiomassWeight'] = pd.to_numeric(calibration_metadata['BiomassWeight'], errors='coerce')
    
    # drop columns with missing values
    calibration_metadata = calibration_metadata.dropna(subset=['ImgName(app)','Species','FileName','ImageUrl','GroundFrameDist'])
    # fixing species naming errors
    calibration_metadata['Species'] = calibration_metadata['Species'].replace({
                                '0.0': 'Other',
                                '0': 'Other',
                                'OTHER': 'Other',
                                'Pea': 'Peas',
                                'Crimnson clover': 'Crimson clover'
                            })
    # drop duplicates
    calibration_metadata = calibration_metadata.drop_duplicates(subset=['FileName','Species'])
    if img_type_list is not None :
        calibration_metadata = calibration_metadata[calibration_metadata['ImageType'].isin(img_type_list)]
    calibration_metadata = calibration_metadata.sort_values(['FileName','Species'],ascending=True)

    return calibration_metadata


def test_duplicate_biomass_fnames(metadata):
    """
        NOTE : This function is a sanity check to see if the preprocessed metadata has any irregularities/ duplicates
    """
    suspicious_fnames = (
    metadata.groupby(['FileName', 'ImageType', 'Species'])
        .size() 
        .reset_index(name='TotalSpeciesEntry')
        .sort_values(["FileName"], ascending=True)
    )
    suspicious_fnames = suspicious_fnames.loc[suspicious_fnames['TotalSpeciesEntry'] > 1]

    assert len(suspicious_fnames) == 0 , f"Suspicious frames found : {suspicious_fnames}"

def reorder_calibration_metadata(metadata):
    """
        NOTE : This function reorders the csv file into a format the model can train on
    """
    pivot_metadata = metadata.pivot_table(
        index=['FileName','ImageUrl','SetId','ImageType','GroundFrameDist','TypeOfCoverCrops'],
        columns='Species',
        values='BiomassWeight',
        aggfunc='first'
    )
    pivot_metadata = pivot_metadata.reset_index()
    pivot_metadata = pivot_metadata.rename_axis(None, axis=1)  # Remove any axis name

    return pivot_metadata

def list_jpg_files(directory):
        return [f for f in os.listdir(directory) if f.lower().endswith('.jpg')]

def generate_popular_mixes(mix_metadata):
    """
        Currently some popular mixes are : 
        Cereal rye, Hairy vetch
        Cereal rye, Crimson clover
        Cereal rye, Winter peas
        Brassica napus, Cereal rye, Hairy vetch
        Brassica napus, Cereal rye, Crimson clover
        Brassica napus, Cereal rye, Winter peas
        Wheat, Hairy vetch
        Wheat, Crimson clover
        Wheat, Winter peas
        Brassica napus, Hairy vetch, Wheat
        Brassica napus, Crimson clover, Wheat
        Brassica napus, Wheat, Winter peas
        Cereal rye
        Wheat

    """

    mix_metadata['Rye-Vetch-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Hairy vetch"])) 
                                                                else None, 
                                                                axis=1
                                                            )

    mix_metadata['Rye-Clover-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Crimson clover"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Rye-Peas-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Winter peas"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    
    mix_metadata['Rye-Vetch-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Hairy vetch"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Rye-Clover-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Crimson clover"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Rye-Peas-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Winter peas"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Vetch-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Hairy vetch"]))
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Clover-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Crimson clover"]))
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Peas-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Winter peas"]))
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Vetch-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Hairy vetch"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Clover-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Crimson clover"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Peas-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Winter peas"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Rye-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Rye-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    mix_metadata['Wheat-Brassica-Mix'] = mix_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    return mix_metadata

def extract_data_from_popular_mix(mix_metadata, column_names: list):
    """
        Extract one/ many mixes from data.
    """
    metadata = mix_metadata.copy()

    # Ensure all provided column names exist in the DataFrame
    valid_columns = [col for col in column_names if col in metadata.columns]

    if not valid_columns:
        raise ValueError("None of the specified columns exist in the DataFrame.")

    # Keep rows where at least one of the specified columns is 1
    metadata = metadata[metadata[valid_columns].eq(1).any(axis=1)]

    # Drop columns that contain only NaN values
    metadata = metadata.dropna(axis=1, how='all')

    return metadata

def export_results_to_csv(results_df: pd.DataFrame, output_csv_path: str, print_results: bool = True) -> pd.DataFrame:
    """
        Clean final results and export to CSV.
    """
    results = results_df.dropna(axis=1, how='all')

    if print_results:
        print(results)

    results.to_csv(output_csv_path, index=False)
    return results
