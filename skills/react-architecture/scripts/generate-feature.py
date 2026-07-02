#!/usr/bin/env python3
import os
import sys
import re

def to_kebab_case(s):
    # Convert camelCase/PascalCase to kebab-case
    s = re.sub(r'(?<!^)(?=[A-Z])', '-', s).lower()
    return s.replace('_', '-')

def to_pascal_case(s):
    # Convert kebab-case/snake_case to PascalCase
    return ''.join(word.capitalize() for word in re.split(r'[-_]', s))

def to_camel_case(s):
    # Convert kebab-case/snake_case to camelCase
    pascal = to_pascal_case(s)
    return pascal[0].lower() + pascal[1:]

def generate_feature(feature_name):
    kebab = to_kebab_case(feature_name)
    pascal = to_pascal_case(kebab)
    camel = to_camel_case(kebab)

    # Check if src folder exists, otherwise use root-level features directory
    base_dir = os.getcwd()
    is_src_based = os.path.exists(os.path.join(base_dir, "src"))
    if is_src_based:
        feature_dir = os.path.abspath(os.path.join(base_dir, "src", "features", kebab))
        display_path = f"src/features/{kebab}"
    else:
        feature_dir = os.path.abspath(os.path.join(base_dir, "features", kebab))
        display_path = f"features/{kebab}"

    if os.path.exists(feature_dir):
        print(f"[!] Error: Feature directory '{kebab}' already exists at {feature_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Generating feature '{kebab}'...")

    # Subdirectories
    subdirs = ["components", "hooks", "api", "types", "utils"]
    for sub in subdirs:
        os.makedirs(os.path.join(feature_dir, sub), exist_ok=True)

    # 1. Component
    comp_dir = os.path.join(feature_dir, "components", pascal)
    os.makedirs(comp_dir, exist_ok=True)
    comp_file = os.path.join(comp_dir, f"{pascal}.tsx")
    with open(comp_file, "w", encoding="utf-8") as f:
        f.write(f"""import {{ use{pascal} }} from "../../hooks/use{pascal}";
import type {{ {pascal}Data }} from "../../types/{kebab}.types";

interface {pascal}Props {{
  title: string;
}}

export function {pascal}({{ title }}: {pascal}Props) {{
  const {{ data, loading }} = use{pascal}();

  if (loading) return <div>Loading {kebab}...</div>;

  return (
    <div className="{kebab}-section">
      <h3>{{title}}</h3>
      {data ? (
        <p>Data loaded successfully: {{data.name}}</p>
      ) : (
        <p>No data available.</p>
      )}
    </div>
  );
}}

export default {pascal};
""")

    # 2. Hook
    hook_file = os.path.join(feature_dir, "hooks", f"use{pascal}.ts")
    with open(hook_file, "w", encoding="utf-8") as f:
        f.write(f"""import {{ useState, useEffect }} from "react";
import {{ {camel}Api }} from "../api/{camel}Api";
import type {{ {pascal}Data }} from "../types/{kebab}.types";

export function use{pascal}() {{
  const [data, setData] = useState<{pascal}Data | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    let active = true;
    setLoading(true);

    async function fetchData() {{
      try {{
        const result = await {camel}Api.getProfile();
        if (active) {{
          setData(result);
        }}
      }} catch (err) {{
        console.error("Error loading {kebab} data:", err);
      }} finally {{
        if (active) {{
          setLoading(false);
        }}
      }}
    }}

    fetchData();
    return () => {{
      active = false;
    }};
  }}, []);

  return {{ data, loading }};
}}

export default use{pascal};
""")

    # 3. API Client
    api_file = os.path.join(feature_dir, "api", f"{camel}Api.ts")
    with open(api_file, "w", encoding="utf-8") as f:
        f.write(f"""import {{ apiClient }} from "@/shared/lib/apiClient";
import type {{ {pascal}Data }} from "../types/{kebab}.types";

export const {camel}Api = {{
  getProfile: async (): Promise<{pascal}Data> => {{
    return apiClient.get<{pascal}Data>("/{kebab}");
  }},
}};

export default {camel}Api;
""")

    # 4. Types
    types_file = os.path.join(feature_dir, "types", f"{kebab}.types.ts")
    with open(types_file, "w", encoding="utf-8") as f:
        f.write(f"""export interface {pascal}Data {{
  id: string;
  name: string;
}}
""")

    # 5. Public index.ts
    index_file = os.path.join(feature_dir, "index.tsx")
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(f"""import {{ {pascal} }} from "./components/{pascal}/{pascal}";

export {{ {pascal} }};
export default {pascal};
""")

    print(f"[+] Successfully generated feature structure at: {display_path}")
    print(f"    - Public API: {display_path}/index.tsx")
    print(f"    - Component: {display_path}/components/{pascal}/{pascal}.tsx")
    print(f"    - Custom Hook: {display_path}/hooks/use{pascal}.ts")
    print(f"    - API client: {display_path}/api/{camel}Api.ts")
    print(f"    - Types: {display_path}/types/{kebab}.types.ts")

    # Check if apiClient base is present to help developer
    api_client_paths = [
        os.path.join(base_dir, "src", "shared", "lib", "apiClient.ts"),
        os.path.join(base_dir, "src", "shared", "lib", "apiClient.tsx"),
        os.path.join(base_dir, "shared", "lib", "apiClient.ts"),
        os.path.join(base_dir, "shared", "lib", "apiClient.tsx"),
    ]
    if not any(os.path.exists(p) for p in api_client_paths):
        print("\n[!] Note: Base apiClient was not found at 'shared/lib/apiClient'.")
        print("    Make sure to create it or update imports in your new API file if using a different API client.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate-feature.py <feature-name>")
        sys.exit(1)
    generate_feature(sys.argv[1])
