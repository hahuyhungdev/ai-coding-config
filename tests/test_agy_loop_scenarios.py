import importlib.util
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_DIR / "scripts" / "agy_loop_scenarios.py"
spec = importlib.util.spec_from_file_location("agy_loop_scenarios", SCRIPT_PATH)
agy_loop_scenarios = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agy_loop_scenarios)


def test_scenarios_cover_known_loop_triggers():
    scenario_ids = set(agy_loop_scenarios.SCENARIOS)

    assert {
        "blocked-read-retry",
        "scratch-magic-index",
        "substring-truncation",
        "hook-bypass-pressure",
        "two-failed-attempts",
    }.issubset(scenario_ids)


def test_scenarios_define_expected_pass_and_fail_signals():
    for scenario in agy_loop_scenarios.SCENARIOS.values():
        assert scenario.prompt.strip()
        assert scenario.pass_signals
        assert scenario.fail_signals


def test_build_agy_command_starts_fresh_print_session():
    command = agy_loop_scenarios.build_agy_command("scratch-magic-index")

    assert command[:3] == ["rtk", "agy", "-p"]
    assert "--conversation" not in command
    assert "scripts/inspect_conversation.py" in command[-1]


def test_format_scenario_list_includes_run_command_hint():
    output = agy_loop_scenarios.format_scenario_list()

    assert "blocked-read-retry" in output
    assert "rtk python3 scripts/agy_loop_scenarios.py --run" in output


def test_unknown_scenario_is_rejected():
    try:
        agy_loop_scenarios.build_agy_command("missing")
    except KeyError as exc:
        assert "Unknown scenario" in str(exc)
    else:
        raise AssertionError("Expected unknown scenario to raise KeyError")
