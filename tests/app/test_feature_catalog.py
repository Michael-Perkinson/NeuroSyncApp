from src.app.catalog import DEFAULT_APP_ID, get_app_definition, iter_app_definitions


def test_feature_catalog_points_to_feature_entrypoints():
    definitions = {definition.app_id: definition for definition in iter_app_definitions()}

    assert DEFAULT_APP_ID == "raw_analysis"
    assert definitions["raw_analysis"].module_path == "src.features.raw_photometry.app"
    assert (
        definitions["single_animal"].module_path
        == "src.features.behaviour_alignment.app"
    )
    assert (
        definitions["telemetry_photom_opto"].module_path
        == "src.features.telemetry_alignment.app"
    )


def test_feature_catalog_still_resolves_known_tool():
    definition = get_app_definition("telemetry_photom_opto")

    assert definition.label == "Align Telemetry Data"
    assert definition.qt_supported is True

