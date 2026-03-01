from astronomical_calendars.cli import main


def test_run_command_executes_pipeline(capsys) -> None:
    exit_code = main(["run", "--calendar", "astronomy-all", "--year", "2026"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate astronomy year=2026" in captured.out
    assert "reconcile astronomy-all year=2026" in captured.out
    assert "build astronomy-all variant_policy=default" in captured.out


def test_build_command_uses_manifest_default_variant_policy(capsys) -> None:
    exit_code = main(["build", "--calendar", "astronomy-eclipses"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "build astronomy-eclipses variant_policy=default" in captured.out
