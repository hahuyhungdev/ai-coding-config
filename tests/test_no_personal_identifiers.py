import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BANNED_IDENTIFIERS = (
    "huy" "hung",
    "huy" "." "hung",
    "/home/" + "huy" + "hung",
    "c:\\users\\" + "huy" + "." + "hung",
    "users/" + "huy" + "." + "hung",
    "huy" "-hung",
    "huy" "_hung",
)


def test_tracked_files_do_not_contain_personal_identifiers():
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    paths = [
        REPO_ROOT / path
        for path in result.stdout.decode("utf-8").split("\0")
        if path
    ]

    matches = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel_path = path.relative_to(REPO_ROOT)
        for line_number, line in enumerate(lines, start=1):
            lower_line = line.lower()
            for identifier in BANNED_IDENTIFIERS:
                if identifier.lower() in lower_line:
                    matches.append(f"{rel_path}:{line_number}: contains personal identifier pattern")
                    break

    assert matches == []
