#!/usr/bin/env python3
import os
import re
import sys


def to_kebab_case(value):
    value = value.strip()
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-").lower()
    if not value:
        raise ValueError("Component name must contain at least one letter or digit.")
    return value


def to_pascal_case(value):
    return "".join(word[:1].upper() + word[1:] for word in value.split("-") if word)


def generate_component(comp_name, target_dir, add_scss=False):
    kebab = to_kebab_case(comp_name)
    pascal = to_pascal_case(kebab)
    
    target_abs = os.path.abspath(os.path.join(os.getcwd(), target_dir, pascal))
    
    if os.path.exists(target_abs):
        print(f"[!] Error: Component directory '{pascal}' already exists at {target_abs}", file=sys.stderr)
        sys.exit(1)
        
    print(f"[*] Generating component '{pascal}' inside {target_dir}...")
    os.makedirs(target_abs, exist_ok=True)
    
    # 1. SCSS file
    scss_import = ""
    if add_scss:
        scss_file = os.path.join(target_abs, f"{pascal}.module.scss")
        with open(scss_file, "w", encoding="utf-8") as f:
            f.write(f".container {{\n  display: block;\n}}\n")
        scss_import = f"import styles from \"./{pascal}.module.scss\";\n\n"
        print(f"[+] Created: {pascal}.module.scss")
        
    # 2. TSX file
    tsx_file = os.path.join(target_abs, "index.tsx")
    with open(tsx_file, "w", encoding="utf-8") as f:
        class_name = "styles.container" if add_scss else f"\"{kebab}-component\""
        f.write(f"""{scss_import}import type {{ ReactNode }} from "react";

interface {pascal}Props {{
  children?: ReactNode;
}}

export function {pascal}({{ children }}: {pascal}Props) {{
  return (
    <div className={{{class_name}}}>
      {{children}}
    </div>
  );
}}

export default {pascal};
""")
    print("[+] Created: index.tsx")
    print(f"[+] Successfully generated component folder at: {target_dir}/{pascal}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate-component.py <ComponentName> <TargetDirectory> [--scss]")
        sys.exit(1)
        
    comp = sys.argv[1]
    target = sys.argv[2]
    scss = "--scss" in sys.argv
    try:
        generate_component(comp, target, scss)
    except ValueError as error:
        print(f"[!] Error: {error}", file=sys.stderr)
        sys.exit(1)
