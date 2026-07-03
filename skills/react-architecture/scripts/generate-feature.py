#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def to_kebab_case(value: str) -> str:
    value = value.strip()
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-").lower()
    if not value:
        raise ValueError("Feature name must contain at least one letter or digit.")
    return value


def to_pascal_case(value: str) -> str:
    return "".join(word[:1].upper() + word[1:] for word in value.split("-") if word)


def to_camel_case(value: str) -> str:
    pascal = to_pascal_case(value)
    return pascal[:1].lower() + pascal[1:]


def write_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def generate_feature(feature_name: str) -> None:
    kebab = to_kebab_case(feature_name)
    pascal = to_pascal_case(kebab)
    camel = to_camel_case(kebab)
    view_name = f"{pascal}View"
    section_name = f"{pascal}Section"
    hook_name = f"use{pascal}"
    api_name = f"{camel}Api"
    type_name = f"{pascal}Data"

    base_dir = Path.cwd()
    source_root = base_dir / "src" if (base_dir / "src").exists() else base_dir
    feature_dir = source_root / "features" / kebab
    display_prefix = "src/" if source_root.name == "src" else ""
    display_path = f"{display_prefix}features/{kebab}"

    if feature_dir.exists():
        print(f"[!] Error: Feature directory '{kebab}' already exists at {feature_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Generating feature '{kebab}'...")

    for subdirectory in ["components", "hooks", "api", "types", "utils"]:
        (feature_dir / subdirectory).mkdir(parents=True, exist_ok=True)

    write_file(
        feature_dir / "components" / view_name / "index.tsx",
        f"""import type {{ {type_name} }} from "../../types/{kebab}.types";

interface {view_name}Props {{
  title: string;
  data: {type_name} | null;
  isLoading: boolean;
}}

export function {view_name}({{ title, data, isLoading }}: {view_name}Props) {{
  if (isLoading) {{
    return (
      <section className="{kebab}-section" aria-busy="true">
        <h3>{{title}}</h3>
        <p>Loading {kebab}...</p>
      </section>
    );
  }}

  return (
    <section className="{kebab}-section">
      <h3>{{title}}</h3>
      {{data ? (
        <p>Data loaded successfully: {{data.name}}</p>
      ) : (
        <p>No data available.</p>
      )}}
    </section>
  );
}}

export default {view_name};
""",
    )

    write_file(
        feature_dir / "hooks" / f"{hook_name}.ts",
        f"""import {{ useEffect, useState }} from "react";
import {{ {api_name} }} from "../api/{api_name}";
import type {{ {type_name} }} from "../types/{kebab}.types";

interface {hook_name[:1].upper() + hook_name[1:]}State {{
  data: {type_name} | null;
  error: Error | null;
  isLoading: boolean;
}}

export function {hook_name}(): {hook_name[:1].upper() + hook_name[1:]}State {{
  const [data, setData] = useState<{type_name} | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {{
    let active = true;

    async function loadData() {{
      setIsLoading(true);
      setError(null);

      try {{
        const result = await {api_name}.getProfile();
        if (active) {{
          setData(result);
        }}
      }} catch (nextError) {{
        if (active) {{
          setError(nextError instanceof Error ? nextError : new Error("Unknown {kebab} error"));
        }}
      }} finally {{
        if (active) {{
          setIsLoading(false);
        }}
      }}
    }}

    loadData();
    return () => {{
      active = false;
    }};
  }}, []);

  return {{ data, error, isLoading }};
}}
""",
    )

    write_file(
        feature_dir / "api" / f"{api_name}.ts",
        f"""import type {{ {type_name} }} from "../types/{kebab}.types";

export const {api_name} = {{
  async getProfile(): Promise<{type_name} | null> {{
    return null;
  }},
}};
""",
    )

    write_file(
        feature_dir / "types" / f"{kebab}.types.ts",
        f"""export interface {type_name} {{
  id: string;
  name: string;
}}
""",
    )

    write_file(
        feature_dir / "index.tsx",
        f"""import {{ {view_name} }} from "./components/{view_name}";
import {{ {hook_name} }} from "./hooks/{hook_name}";

interface {section_name}Props {{
  title?: string;
}}

export function {section_name}({{ title = "{pascal}" }}: {section_name}Props) {{
  const {{ data, isLoading }} = {hook_name}();

  return <{view_name} title={{title}} data={{data}} isLoading={{isLoading}} />;
}}

export default {section_name};
""",
    )

    print(f"[+] Successfully generated feature structure at: {display_path}")
    print(f"    - Public component: {display_path}/index.tsx")
    print(f"    - View component: {display_path}/components/{view_name}/index.tsx")
    print(f"    - Custom hook: {display_path}/hooks/{hook_name}.ts")
    print(f"    - API client: {display_path}/api/{api_name}.ts")
    print(f"    - Types: {display_path}/types/{kebab}.types.ts")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate-feature.py <feature-name>")
        sys.exit(1)

    try:
        generate_feature(sys.argv[1])
    except ValueError as error:
        print(f"[!] Error: {error}", file=sys.stderr)
        sys.exit(1)
