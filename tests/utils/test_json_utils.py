import json
import pytest
import pandas as pd

from src.data.json_handler import save_behaviour_static_inputs, load_behaviour_static_inputs


def test_save_behaviour_static_inputs_valid(tmp_path):
    # Define a valid DataFrame
    test_df = pd.DataFrame({
        'Behaviour Name': ['Walking', 'Running', 'Eating'],
        'Pre Behaviour Time': [5, 10, 15],
        'Post Behaviour Time': [5, 10, 15],
        'Bin Size': [1, 2, 3]
    })

    # Define the expected output
    output_df = {
        'Walking': [5, 5, 1],
        'Running': [10, 10, 2],
        'Eating': [15, 15, 3]
    }

    # Generate the file path
    file_path = tmp_path / "behaviour_settings.json"

    # Call the function
    save_behaviour_static_inputs(test_df, file_path)

    # Assert: Check if the file was created
    assert file_path.exists(), "File was not created"

    # Assert: Verify the file content matches the expected output
    with open(file_path, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == output_df, "File content does not match the expected data"

def test_save_behaviour_static_inputs_empty(tmp_path):
    # Generate the file path
    file_path = tmp_path / "behaviour_settings.json"

    # Call the function
    save_behaviour_static_inputs(pd.DataFrame(), file_path)

    # Assert: Check if the file was created
    assert file_path.exists(), "File was not created"

    # Assert: Verify the file content is empty
    with open(file_path, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == {}, "File content is not empty"

def test_load_behaviour_static_inputs_valid(tmp_path):
    # Define the expected output
    output_df = {
        'Walking': {
            'pre_behaviour_time': 5,
            'post_behaviour_time': 5,
            'bin_size': 1
        },
        'Running': {
            'pre_behaviour_time': 10,
            'post_behaviour_time': 10,
            'bin_size': 2
        },
        'Eating': {
            'pre_behaviour_time': 15,
            'post_behaviour_time': 15,
            'bin_size': 3
        }
    }

    # Generate the file path
    filename = tmp_path / "behaviour_settings.json"

    # Save the data to the file
    with open(filename, 'w') as f:
        json.dump({
            'Walking': [5, 5, 1],
            'Running': [10, 10, 2],
            'Eating': [15, 15, 3]
        }, f)

    # Call the function
    loaded_data = load_behaviour_static_inputs(filename)

    # Assert: Verify the loaded data matches the expected output
    assert loaded_data == output_df, "Loaded data does not match the expected data"


def test_load_behaviour_static_inputs_file_missing(tmp_path):
    filename = tmp_path / "missing_behaviour_settings.json"
    loaded_data = load_behaviour_static_inputs(filename)
    assert loaded_data == {}, "Expected empty dictionary for missing file"


def test_load_behaviour_static_inputs_invalid_json(tmp_path):
    filename = tmp_path / "behaviour_settings.json"
    with open(filename, 'w') as f:
        f.write("INVALID_JSON")

    loaded_data = load_behaviour_static_inputs(filename)
    assert loaded_data == {}, "Expected empty dictionary for invalid JSON file"
