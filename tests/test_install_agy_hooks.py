import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


def load_install_agy_module():
    module_path = Path(__file__).resolve().parents[1] / "install-agy.py"
    spec = importlib.util.spec_from_file_location("install_agy", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestInstallAgyHooks(unittest.TestCase):
    def test_configures_quota_hooks_in_official_and_runtime_settings(self):
        install_agy = load_install_agy_module()

        with TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            agy_cli_dir = home / ".gemini" / "antigravity-cli"
            agy_cli_dir.mkdir(parents=True)
            official_settings = home / ".gemini" / "settings.json"
            runtime_settings = agy_cli_dir / "settings.json"
            official_settings.parent.mkdir(parents=True, exist_ok=True)
            runtime_settings.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "run_command",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "python3 graphify_pre_tool.py",
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            install_agy.configure_quota_hooks(home, agy_cli_dir)
            install_agy.configure_quota_hooks(home, agy_cli_dir)

            for settings_file in (official_settings, runtime_settings):
                data = json.loads(settings_file.read_text(encoding="utf-8"))
                hooks = data["hooks"]
                for event, name, script in (
                    ("UserPromptSubmit", "quota-pre-check", "before_agent.py"),
                    ("Stop", "quota-auto-switch", "after_agent.py"),
                ):
                    matching_hooks = [
                        hook
                        for entry in hooks[event]
                        if entry.get("matcher") == "*"
                        for hook in entry.get("hooks", [])
                        if hook.get("name") == name
                    ]
                    self.assertEqual(len(matching_hooks), 1)
                    self.assertEqual(
                        matching_hooks[0]["command"],
                        f"python3 {agy_cli_dir}/{script}",
                    )

            runtime_data = json.loads(runtime_settings.read_text(encoding="utf-8"))
            self.assertIn("PreToolUse", runtime_data["hooks"])


if __name__ == "__main__":
    unittest.main()
