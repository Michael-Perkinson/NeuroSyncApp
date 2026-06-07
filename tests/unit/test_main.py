import main


def test_main_prefers_qt_dashboard_when_available(monkeypatch):
    dashboard_calls = []

    monkeypatch.setattr(main, "_is_pyside6_available", lambda: True)
    monkeypatch.setattr(
        main,
        "run_dashboard",
        lambda: dashboard_calls.append("qt") or 0,
    )

    assert main.main([]) == 0
    assert dashboard_calls == ["qt"]


def test_main_uses_tool_runner_for_direct_tool_launch(monkeypatch):
    tool_calls = []

    monkeypatch.setattr(main, "_is_pyside6_available", lambda: True)
    monkeypatch.setattr(
        main,
        "run_tool_window",
        lambda tool_id: tool_calls.append(tool_id) or 0,
    )

    assert main.main(["--tool", "single_animal", "--framework", "qt"]) == 0
    assert tool_calls == ["single_animal"]
