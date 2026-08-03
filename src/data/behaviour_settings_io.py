"""Save and load behaviour settings between a DataFrame and JSON."""

import json
import logging
import os
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def save_behaviour_static_inputs(dataframe: pd.DataFrame, filename: str | os.PathLike[str]) -> None:
    """Save behaviour settings from a DataFrame to a JSON file."""
    if dataframe.empty:
        save_dict_to_json({}, filename)
        return

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


def save_dict_to_json(data: dict[str, Any], filename: str | os.PathLike[str]) -> None:
    """Save a dictionary to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4)
    except (OSError, TypeError, ValueError):
        logger.exception("Error saving JSON file %s", filename)


def load_behaviour_static_inputs(filename: str | os.PathLike[str]) -> dict[str, dict[str, Any]]:
    """Load behaviour settings from a JSON file, or {} if the file is missing or invalid."""
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


def open_json_to_dict(filename: str | os.PathLike[str]) -> dict[str, Any]:
    """Open a JSON file and return its data as a dictionary, or {} if missing or unparsable."""
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        return data
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Error loading JSON file %s: %s", filename, e)
        return {}
