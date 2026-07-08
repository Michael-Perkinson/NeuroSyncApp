"""Unit tests for remembered signal-column selections."""

import importlib


def _fresh_module(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROSYNCAPP_CONFIG_DIR", str(tmp_path))
    import src.shared.persistence.app_paths as app_paths
    import src.shared.persistence.column_selection_memory as memory
    importlib.reload(app_paths)
    importlib.reload(memory)
    return memory


def test_recall_none_before_anything_saved(tmp_path, monkeypatch):
    memory = _fresh_module(tmp_path, monkeypatch)
    assert memory.recall_selection(["dFoF_465", "dFoF_405"]) is None


def test_remember_then_recall_is_order_independent(tmp_path, monkeypatch):
    memory = _fresh_module(tmp_path, monkeypatch)
    columns = ["dFoF_465", "dFoF_405", "405", "465"]
    memory.remember_selection(columns, ["dFoF_465", "dFoF_405"])
    # Same set, different order, still recalls and preserves saved order.
    assert memory.recall_selection(list(reversed(columns))) == ["dFoF_465", "dFoF_405"]


def test_different_column_set_does_not_match(tmp_path, monkeypatch):
    memory = _fresh_module(tmp_path, monkeypatch)
    memory.remember_selection(["dFoF_465", "dFoF_405"], ["dFoF_465"])
    assert memory.recall_selection(["sig_a", "sig_b"]) is None


def test_empty_inputs_are_noops(tmp_path, monkeypatch):
    memory = _fresh_module(tmp_path, monkeypatch)
    memory.remember_selection([], ["x"])
    memory.remember_selection(["a", "b"], [])
    assert memory.recall_selection([]) is None
    assert memory.recall_selection(["a", "b"]) is None
