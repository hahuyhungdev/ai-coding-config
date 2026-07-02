#!/usr/bin/env python3
import json
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SKILLS_JSON_PATH = REPO_DIR / "skills.json"

TEST_CASES = [
    # Vague cases
    {
        "prompt": "Hãy tối ưu hóa code và làm giao diện đẹp hơn nhé",
        "expected_skills": ["ui-ux-design", "karpathy-guidelines"]
    },
    {
        "prompt": "sửa lại mấy cái components cho gọn",
        "expected_skills": ["react-architecture", "react-pattern"]
    },
    # Description cases
    {
        "prompt": "please improve ui ux of this page",
        "expected_skills": ["ui-ux-design"]
    },
    {
        "prompt": "I want to refactor the state management pattern inside the component",
        "expected_skills": ["react-pattern", "karpathy-guidelines", "react-architecture"]
    },
    {
        "prompt": "please check color contrast and button loading states for accessibility",
        "expected_skills": ["ui-ux-design"]
    },
    {
        "prompt": "let's run a test with playwright",
        "expected_skills": ["playwright"]
    },
    # Direct mention cases
    {
        "prompt": "use the react-pattern skill",
        "expected_skills": ["react-pattern"]
    },
    {
        "prompt": "apply react-architecture here",
        "expected_skills": ["react-architecture"]
    },
    {
        "prompt": "check ui-ux-design for rules",
        "expected_skills": ["ui-ux-design"]
    },
    {
        "prompt": "quét giao diện website và lưu report",
        "expected_skills": ["frontend-scan"]
    },
    {
        "prompt": "design a new endpoint and check database caching",
        "expected_skills": ["backend-pattern"]
    },
    {
        "prompt": "apply backend-pattern guidelines",
        "expected_skills": ["backend-pattern"]
    },
    {
        "prompt": "run TDD red green cycle and compile",
        "expected_skills": ["quality-gate"]
    },
    {
        "prompt": "verify changes before creating PR",
        "expected_skills": ["quality-gate"]
    },
    {
        "prompt": "compact session context rollover",
        "expected_skills": ["context-budget"]
    }
]

def simulate_trigger(prompt, skills):
    prompt_lower = prompt.lower()
    triggered = []
    for skill in skills:
        name = skill["name"]
        triggers = skill.get("triggers", {})
        keywords = triggers.get("keywords", [])
        
        # Check if skill name or any keyword is in the prompt
        matched = False
        if name.lower() in prompt_lower:
            matched = True
        else:
            for kw in keywords:
                if kw.lower() in prompt_lower:
                    matched = True
                    break
        if matched:
            triggered.append(name)
    return triggered

def main():
    if not SKILLS_JSON_PATH.exists():
        print(f"Error: {SKILLS_JSON_PATH} not found.")
        return
        
    with open(SKILLS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    skills = data.get("skills", [])
    print(f"Loaded {len(skills)} skills for trigger simulation.\n")
    
    passed_all = True
    for i, case in enumerate(TEST_CASES):
        prompt = case["prompt"]
        expected = case["expected_skills"]
        triggered = simulate_trigger(prompt, skills)
        
        # Check if all expected are in triggered
        missing = [exp for exp in expected if exp not in triggered]
        
        print(f"Test Case {i+1}:")
        print(f"  Prompt: '{prompt}'")
        print(f"  Expected: {expected}")
        print(f"  Triggered: {triggered}")
        if not missing:
            print("  Result: PASS [OK]")
        else:
            print(f"  Result: FAIL [ERROR] (Missing: {missing})")
            passed_all = False
        print("-" * 50)
        
    if passed_all:
        print("\nAll trigger simulation tests PASSED successfully! [SUCCESS]")
    else:
        print("\nSome trigger simulation tests FAILED. Review keyword mapping. [FAILED]")

if __name__ == "__main__":
    main()
