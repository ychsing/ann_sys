import os
import hashlib

BASE_DIR = "user_data"

def get_user_dir(user_email: str) -> str:
    os.makedirs(BASE_DIR, exist_ok=True)
    uid = hashlib.sha256(user_email.encode()).hexdigest()[:16]
    user_dir = os.path.join(BASE_DIR, uid)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_working_file(user_email: str) -> str:
    return os.path.join(get_user_dir(user_email), "working.json")
