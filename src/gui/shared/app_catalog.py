from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Iterator


@dataclass(frozen=True)
class AppDefinition:
    app_id: str
    label: str
    module_path: str | None
    class_name: str | None
    qt_supported: bool = False
    description: str = ""

    def load_widget_class(self):
        if not self.qt_supported or not self.module_path or not self.class_name:
            raise NotImplementedError(
                f"Tool '{self.app_id}' has not been ported to PySide6 yet."
            )

        module = import_module(self.module_path)
        return getattr(module, self.class_name)


APP_DEFINITIONS = (
    AppDefinition(
        app_id="raw_analysis",
        label="Analyse Raw Data",
        module_path="src.main_apps.raw_photometry_processing_qt",
        class_name="RawPhotometryProcessingQt",
        qt_supported=True,
        description="Inspect raw photometry recordings and choose an analysis window.",
    ),
    AppDefinition(
        app_id="single_animal",
        label="Align Photometry and Behaviour",
        module_path="src.main_apps.align_photometry_behaviour",
        class_name="DataProcessingSingleInstance",
        qt_supported=True,
        description="Align photometry recordings with coded behaviour events.",
    ),
    AppDefinition(
        app_id="telemetry_photom_opto",
        label="Align Telemetry Data",
        module_path="src.main_apps.align_telemetry_photom_opto",
        class_name="TelemetryPhotomOptoProcessingApp",
        qt_supported=True,
        description="Align telemetry, photometry, and optogenetic recordings.",
    ),
    AppDefinition(
        app_id="combine_data",
        label="Combine Data",
        module_path=None,
        class_name=None,
        qt_supported=False,
        description="Qt rewrite in progress.",
    ),
)

DEFAULT_APP_ID = "raw_analysis"


def iter_app_definitions() -> Iterator[AppDefinition]:
    yield from APP_DEFINITIONS


def get_app_definition(app_id: str) -> AppDefinition:
    for definition in APP_DEFINITIONS:
        if definition.app_id == app_id:
            return definition
    raise ValueError(f"Unknown app id: {app_id}")
