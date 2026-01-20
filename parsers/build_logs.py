# parsers/build_logs.py
# Robust, case-insensitive parsing of typical GCC/Clang/LD output.

import re
from typing import Dict, List

# Match common error/warning patterns from compiler and linker
ERROR_PATTERNS = [
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"undefined reference", re.IGNORECASE),
    re.compile(r"ld returned [0-9]+ exit status", re.IGNORECASE),
]
WARNING_PATTERNS = [
    re.compile(r"\bwarning\b", re.IGNORECASE),
]

def parse_build_log(text: str) -> Dict[str, List[str]]:
    """
    Return a dict with 'errors' and 'warnings' lists extracted from a build log.
    """
    errors: List[str] = []
    warnings: List[str] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Order matters: classify as error first if both appear
        if any(p.search(line) for p in ERROR_PATTERNS):
            errors.append(line)
        elif any(p.search(line) for p in WARNING_PATTERNS):
            warnings.append(line)

    return {"errors": errors, "warnings": warnings}