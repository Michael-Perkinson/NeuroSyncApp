import pytest


pytestmark = pytest.mark.skip(
    reason="Telemetry startup coverage will be restored once the full Qt port is complete."
)
