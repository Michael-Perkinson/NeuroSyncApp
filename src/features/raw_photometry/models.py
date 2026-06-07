"""Feature-local model exports for raw photometry processing."""

from dataclasses import dataclass


@dataclass
class RawPhotometryViewState:
    selected_file: str = ""
    selected_result_csv: str = ""
