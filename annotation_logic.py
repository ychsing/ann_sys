from datetime import datetime

def save_annotation_for_user(case, user_email, final_data):
    case.setdefault("annotation", {})
    by_user = case["annotation"].setdefault("by_user", {})

    prev = by_user.get(user_email)
    if prev and prev.get("data") == final_data:
        return False  # 沒變

    by_user[user_email] = {
        "data": final_data,
        "updated_at": datetime.now().isoformat()
    }

    case["annotation"]["verified"] = True
    case["annotation"]["verified_at"] = datetime.now().isoformat()
    case["annotation"]["verified_by"] = user_email

    return True