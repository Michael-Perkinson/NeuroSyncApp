"""
json_handler.py

This module provides functions for handling JSON files, focusing on saving and loading
behaviour settings to/from JSON. It integrates with pandas DataFrames for streamlined
data processing.

Functions:
- open_json_to_dict: Opens a JSON file and returns its contents as a dictionary.
- save_dict_to_json: Saves a dictionary to a JSON file.
- save_behaviour_static_inputs: Saves behaviour settings from a DataFrame to a JSON file.
- load_behaviour_static_inputs: Loads behaviour settings from a JSON file into a dictionary.
"""

import json
import logging
import os
from typing import Any, Dict
import pandas as pd


logger = logging.getLogger(__name__)


def save_behaviour_static_inputs(dataframe: pd.DataFrame, filename: str) -> None:
    """
    Save behaviour settings from a DataFrame to a JSON file.

    Parameters:
    - dataframe (pd.DataFrame): The DataFrame containing behaviour settings.
    - filename (str): The path to the JSON file to save the settings.
    """
    if dataframe.empty:
        # Handle empty DataFrame
        save_dict_to_json({}, filename)
        return

    # Process the DataFrame to create the JSON structure
    behaviour_data = {
        behaviour_name: (pre_time, post_time, bin_size)
        for behaviour_name, pre_time, post_time, bin_size
        in zip(
            dataframe['Behaviour Name'],
            dataframe['Pre Behaviour Time'],
            dataframe['Post Behaviour Time'],
            dataframe['Bin Size']
        )
    }
    save_dict_to_json(behaviour_data, filename)


def save_dict_to_json(data: Dict[str, Any], filename: str) -> None:
    """
    Save a dictionary to a JSON file.

    Parameters:
    - data (Dict[str, Any]): The data to save.
    - filename (str): The path to the file where the data will be saved.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4)
    except IOError as e:
        logger.exception("Error saving JSON file %s", filename)


def load_behaviour_static_inputs(filename: str) -> Dict[str, Dict[str, Any]]:
    """
    Load behaviour settings from a JSON file into a dictionary.

    Parameters:
    - filename (str): The path to the JSON file.

    Returns:
    - Dict[str, Dict[str, Any]]: A dictionary containing the behaviour settings
      or an empty dictionary if the file doesn't exist or is invalid.
    """
    behaviour_data = open_json_to_dict(filename)

    if not behaviour_data:
        return {}

    behaviour_settings = {
        behaviour_name: {
            'pre_behaviour_time': settings[0],
            'post_behaviour_time': settings[1],
            'bin_size': settings[2]
        }
        for behaviour_name, settings in behaviour_data.items()
    }
    return behaviour_settings


def open_json_to_dict(filename: str) -> Dict[str, Any]:
    """
    Open a JSON file and return its data as a dictionary.

    Parameters:
    - filename (str): The path to the JSON file.

    Returns:
    - Dict[str, Any]: A dictionary containing the file data, or an empty dictionary
      if the file doesn't exist or cannot be parsed.
    """
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Error loading JSON file %s: %s", filename, e)
        return {}
