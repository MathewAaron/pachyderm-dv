#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
import requests
import sys, os
import shutil
import yaml

def read_yaml(path: str) -> dict:
    """Reads a YAML file and returns its content as a dictionary."""
    try:
        with open(path, "r") as file:
            data = yaml.safe_load(file)
        return data
    except Exception as e:
        raise FileNotFoundError(f"File does not exist : {path}")

def read_csv_as_df(path: str) -> pd.DataFrame:
    """Reads a CSV file into a pandas DataFrame."""
    try:
        csv_reader = pd.read_csv(path, low_memory=False)
        # Return as dataframe
        return csv_reader
    except Exception as e:
        raise FileNotFoundError(f"File does not exist : {path}")
    
def create_dir(dir_path):

    if not Path(dir_path).exists():
        Path(dir_path).mkdir(exist_ok=True, parents=True)

def download_from_url(image_url: str, savedir: str = ".") -> None:
    """Downloads an image from a URL and saves it to the specified directory."""
    create_dir(savedir)
    fname = Path(image_url).name
    fpath = Path(savedir, fname)
    # Send a GET request to the image URL
    response = requests.get(image_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Open a file in binary write mode
        with open(fpath, "wb") as file:
            # Write the content of the response to the file
            file.write(response.content)
    else:
        print(f"Failed to download image from {image_url}")

def mv_img_to_subfolder(image_path,dir_path):

    if not Path(dir_path).exists():
        Path(dir_path).mkdir(exist_ok=True, parents=True)

    if os.path.isfile(image_path) and os.path.exists(dir_path):
        shutil.move(image_path,dir_path)
    else: 
        print("path or dir does not exists!")