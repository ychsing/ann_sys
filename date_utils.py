import re
from datetime import datetime

def normalize_date_to_ymd(s):
    if not s:
        return None, False
    s = str(s).strip()

    patterns = [
        r"(\d{4})(\d{2})(\d{2})",
        r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})"
    ]

    for p in patterns:
        m = re.fullmatch(p, s)
        if m:
            y, mth, d = map(int, m.groups())
            try:
                dt = datetime(y, mth, d)
                return dt.strftime("%Y-%m-%d"), True
            except ValueError:
                return s, False

    return s, False
