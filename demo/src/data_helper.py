#!/usr/bin/env python3

import pandas as pd
from from_root import from_here
import os, sys
sys.path.append(str(from_here('dp_utils')))
from pm3d_utils import *

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
    pm3d_suspicious_fnames = (
    metadata.groupby(['FileName', 'ImageType', 'Species'])
        .size() 
        .reset_index(name='TotalSpeciesEntry')
        .sort_values(["FileName"], ascending=True)
    )
    pm3d_suspicious_fnames = pm3d_suspicious_fnames.loc[pm3d_suspicious_fnames['TotalSpeciesEntry'] > 1]

    assert len(pm3d_suspicious_fnames) == 0 , f"Suspicious frames found : {pm3d_suspicious_fnames}"

def reorder_calibration_metadata(metadata):
    """
        NOTE : This function reorders the csv file into a format the MTL model can train on
    """
    pm3d_pivot_metadata = metadata.pivot_table(
        index=['FileName','ImageUrl','SetId','ImageType','GroundFrameDist','TypeOfCoverCrops'],
        columns='Species',
        values='BiomassWeight',
        aggfunc='first'
    )
    pm3d_pivot_metadata = pm3d_pivot_metadata.reset_index()
    pm3d_pivot_metadata = pm3d_pivot_metadata.rename_axis(None, axis=1)  # Remove any axis name

    return pm3d_pivot_metadata

def list_jpg_files(directory):
        return [f for f in os.listdir(directory) if f.lower().endswith('.jpg')]

def generate_pm3d_popular_mixes(pm3d_metadata):
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

    pm3d_metadata['Rye-Vetch-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Hairy vetch"])) 
                                                                else None, 
                                                                axis=1
                                                            )

    pm3d_metadata['Rye-Clover-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Crimson clover"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Rye-Peas-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Winter peas"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    
    pm3d_metadata['Rye-Vetch-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Hairy vetch"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Rye-Clover-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Crimson clover"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Rye-Peas-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Winter peas"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Vetch-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Hairy vetch"]))
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Clover-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Crimson clover"]))
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Peas-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Winter peas"]))
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Vetch-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Hairy vetch"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Clover-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Crimson clover"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Peas-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Winter peas"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Rye-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Rye-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Cereal rye"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    pm3d_metadata['Wheat-Brassica-Mix'] = pm3d_metadata.apply(
                                                                lambda row: 1 if (pd.notna(row["Wheat"])) and 
                                                                                (pd.notna(row["Brassica napus"])) 
                                                                else None, 
                                                                axis=1
                                                            )
    return pm3d_metadata

def extract_data_from_popular_mix(pm3d_metadata, column_names: list):
    """
        Extract one/ many mixes from pm3d data.
    """
    metadata = pm3d_metadata.copy()

    # Ensure all provided column names exist in the DataFrame
    valid_columns = [col for col in column_names if col in metadata.columns]

    if not valid_columns:
        raise ValueError("None of the specified columns exist in the DataFrame.")

    # Keep rows where at least one of the specified columns is 1
    metadata = metadata[metadata[valid_columns].eq(1).any(axis=1)]

    # Drop columns that contain only NaN values
    metadata = metadata.dropna(axis=1, how='all')

    return metadata

## Example Usage

# if __name__ == '__main__' : 

#     pm3d_raw_data = read_csv_as_df('/home/asmathew/PlantMap3D-CV-Pipeline/pm3d-training-data.csv')
#     extract_ny_jannik = read_csv_as_df('/home/asmathew/PlantMap3D-CV-Pipeline/NYJannink_oats_peas_2024-06-07_images.csv')
#     test_data = preprocess_calibration_data(pm3d_raw_data)
#     test_duplicate_biomass_fnames(test_data)
#     reorder_test = reorder_calibration_metadata(test_data)
#     mix_test = generate_pm3d_popular_mixes(reorder_test)
    
#     ny_jannik = mix_test[mix_test['FileName'].isin(extract_ny_jannik['FileName'])]
#     ny_jannik = ny_jannik.dropna(axis=1, how='all')
#     ny_jannik.to_csv('ny_jannik_data.csv',index=False)
#     print(ny_jannik)