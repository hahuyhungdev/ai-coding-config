import json
from pathlib import Path
import toml
from .constants import REPO_DIR, AGENTS_DIR, SKILLS_DIR, CLI_CONFIGS

def list_agents() -> list[str]:
    if AGENTS_DIR.exists():
        return sorted([f.stem for f in AGENTS_DIR.glob("*.md")])
    return []

def list_skills() -> list[str]:
    if SKILLS_DIR.exists():
        return sorted([d.name for d in SKILLS_DIR.iterdir() if d.is_dir()])
    return []

def parse_markdown_frontmatter(path: Path) -> dict:
    if not path.exists():
        return {}
    metadata = {}
    try:
        content = path.read_text()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return metadata

def load_markdown_content(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        content = path.read_text()
        metadata = parse_markdown_frontmatter(path)
        prompt = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                prompt = parts[2].strip()
        return {"metadata": metadata, "prompt": prompt}
    except Exception:
        return {"metadata": {}, "prompt": ""}


def load_claude_settings() -> dict:
    template_path = REPO_DIR / "claude" / "settings.json"
    try:
        with open(template_path) as f:
            return json.load(f)
    except Exception:
        return {}

def save_claude_settings(data: dict) -> None:
    template_path = REPO_DIR / "claude" / "settings.json"
    try:
        with open(template_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception:
        pass

def load_gemini_settings() -> dict:
    template_path = REPO_DIR / "gemini" / "settings.json"
    try:
        with open(template_path) as f:
            return json.load(f)
    except Exception:
        return {}

def save_gemini_settings(data: dict) -> None:
    template_path = REPO_DIR / "gemini" / "settings.json"
    try:
        with open(template_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception:
        pass

def load_codex_settings() -> dict:
    template_path = REPO_DIR / "codex" / "config.toml"
    try:
        with open(template_path) as f:
            return toml.load(f)
    except Exception:
        return {}

def update_toml_value(file_path: Path, section: str | None, key: str, value: any) -> None:
    if not file_path.exists():
        return
    lines = file_path.read_text().splitlines()
    
    current_section = None
    updated = False
    
    if isinstance(value, str):
        new_value_str = f'"{value}"'
    elif isinstance(value, bool):
        new_value_str = "true" if value else "false"
    else:
        new_value_str = str(value)
        
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            continue
            
        if current_section == section:
            if "=" in line:
                parts = line.split("=", 1)
                k = parts[0].strip()
                if k == key:
                    comment = ""
                    if "#" in parts[1]:
                        comment = "  " + parts[1].split("#", 1)[1]
                    line_comment = f" #{comment}" if comment else ""
                    lines[i] = f"{parts[0].split('=')[0]}= {new_value_str}{line_comment}"
                    updated = True
                    break
                    
    if updated:
        file_path.write_text("\n".join(lines) + "\n")

def get_targets_state() -> dict:
    cli_state = {}
    for cid, info in CLI_CONFIGS.items():
        path_str = info["dir"].replace("~", str(Path.home()))
        cli_state[cid] = Path(path_str).exists()
    
    if not any(cli_state.values()):
        cli_state = {cid: True for cid in CLI_CONFIGS}
    return cli_state
