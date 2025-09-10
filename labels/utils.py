# labels/utils.py
import re

def slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-{2,}", "-", s)
    return s

def pad(n: int, w: int = 3) -> str:
    return str(n).zfill(w)
