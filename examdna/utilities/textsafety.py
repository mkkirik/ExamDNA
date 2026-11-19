"""Detection of instruction-like text inside untrusted source documents.

Uploaded exams are data. If a document contains text that looks like it is
addressed to an AI agent (e.g. "ignore previous instructions"), ExamDNA does
not obey it; it records a security flag so the agent and the user can see it.
Detection is pattern-based and therefore incomplete: it is a tripwire, not a
guarantee.
"""

from __future__ import annotations

import re
from typing import List

_PATTERNS = [
    (r"\bignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|prompts?|rules)", "instruction_override"),
    (r"\bdisregard (all |the )?(previous|prior|above|system)", "instruction_override"),
    (r"\byou are now\b|\bact as (an? )?(system|admin|developer)", "role_hijack"),
    (r"\bsystem prompt\b|\bdeveloper message\b", "prompt_reference"),
    (r"\b(run|execute) (the following|this) (command|code|script)", "command_execution"),
    (r"\brm\s+-rf\b|\bcurl\s+https?://|\bwget\s+https?://|\bpowershell\s+-", "command_execution"),
    (r"\b(api[_ -]?key|password|secret token|access token)s?\b", "secret_request"),
    (r"\b(send|upload|post|exfiltrate) (it|this|the (data|files?|contents?)) to\b", "exfiltration"),
    (r"\b(read|open|cat) (~|/etc/|c:\\\\|\.ssh|\.env)", "file_access"),
]
_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in _PATTERNS]


def scan_for_injection(text: str) -> List[str]:
    """Return sorted unique flag labels found in ``text``."""
    if not text:
        return []
    found = {label for rx, label in _COMPILED if rx.search(text)}
    return sorted(found)
