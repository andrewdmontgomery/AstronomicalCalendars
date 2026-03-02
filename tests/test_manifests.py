from astrocal.manifests import load_manifest


def test_load_astronomy_all_manifest_uses_astronomy_only() -> None:
    manifest = load_manifest("astronomy-all")

    assert manifest.name == "astronomy-all"
    assert manifest.source_types == ["astronomy"]
    assert manifest.source_names == ["moon-phases", "seasons", "eclipses"]
    assert manifest.variant_policy == "default"


def test_load_specific_phase_one_manifest() -> None:
    manifest = load_manifest("astronomy-moon-phases")

    assert manifest.event_types == ["moon-phase"]
    assert manifest.source_names == ["moon-phases"]
    assert manifest.output == "calendars/moon-phases.ics"
