import json

def load_cases(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cases(path, cases):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

def is_verified(case):
    return bool(case.get("annotation", {}).get("by_user"))

def find_first_unverified_index(cases, case_ids):
    for i, cid in enumerate(case_ids):
        if not is_verified(cases[cid]):
            return i
    return 0