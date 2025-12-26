import json
import os

def load_cases(working_file):
    if not os.path.exists(working_file):
        return None

    try:
        with open(working_file, "r", encoding="utf-8") as f:
            cases = json.load(f)
    except Exception:
        return None

    if not isinstance(cases, dict):
        return None

    return cases

def save_cases(working_file, cases):
    with open(working_file, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

def is_verified(case):
    return bool(case.get("annotation", {}).get("by_user"))

def find_first_unverified_index(cases, case_ids):
    for i, cid in enumerate(case_ids):
        if not is_verified(cases[cid]):
            return i
    return 0