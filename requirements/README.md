# Tested Package Snapshots

`pyproject.toml` is the source of truth for dependencies.

These files are resolved package snapshots for CPython 3.14:

- `windows-py314.txt`: validated with pip for `win_amd64`
- `macos-py314.txt`: validated with pip for both `macosx_14_0_arm64` and `macosx_14_0_x86_64`

Use the snapshots when you need to recreate a known tested environment:

```bash
python -m pip install -r requirements/windows-py314.txt
```

For development, prefer:

```bash
python -m pip install -e ".[dev]"
```
