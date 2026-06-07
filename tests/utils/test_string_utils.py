import pytest
from src.string_ops.string_utils import normalize_deduplicate_and_order_strings

@pytest.mark.parametrize("input_behaviours, expected_output", [
    (["walking", "RUNNING", "EaTing"], ["Eating", "Running", "Walking"]),
    ([], []),
    (["cat", "Cat", "bat"], ["Bat", "Cat"]),
    ([" walking ", "running"], ["Running", "Walking"]),
    (["!Walking", "$running"], ["Running", "Walking"]),
    (["----", "----"], []),
])
def test_normalize_deduplicate_and_order_strings(input_behaviours, expected_output):
    assert normalize_deduplicate_and_order_strings(
        input_behaviours) == expected_output
