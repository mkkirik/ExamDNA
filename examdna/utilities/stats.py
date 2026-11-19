"""Small, dependency-free statistics and similarity helpers.

All similarity functions are documented in docs/methodology.md. They are
transparent set/sequence measures, not learned semantic models.
"""

from __future__ import annotations

import difflib
import re
import statistics
from collections import Counter
from typing import Dict, Hashable, Iterable, List, Optional, Sequence

_WORD = re.compile(r"[\w']+", re.UNICODE)


def mean(values: Sequence[float]) -> Optional[float]:
    return round(statistics.fmean(values), 3) if values else None


def median(values: Sequence[float]) -> Optional[float]:
    return round(float(statistics.median(values)), 3) if values else None


def summary(values: Sequence[float]) -> Dict[str, Optional[float]]:
    vals = [v for v in values if v is not None]
    return {
        "n": len(vals),
        "mean": mean(vals),
        "median": median(vals),
        "min": min(vals) if vals else None,
        "max": max(vals) if vals else None,
    }


def frequency(items: Iterable[Hashable]) -> Dict[str, int]:
    counts = Counter(str(i) for i in items if i is not None and i != "")
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def proportions(counts: Dict[str, float]) -> Dict[str, float]:
    total = float(sum(counts.values()))
    if total <= 0:
        return {k: 0.0 for k in counts}
    return {k: round(v / total, 4) for k, v in counts.items()}


def total_variation(p: Dict[str, float], q: Dict[str, float]) -> float:
    """Total variation distance between two discrete distributions (0..1).

    Inputs are normalised first, so raw counts may be passed.
    """
    p_n, q_n = _normalise(p), _normalise(q)
    keys = set(p_n) | set(q_n)
    if not keys:
        return 0.0
    return round(0.5 * sum(abs(p_n.get(k, 0.0) - q_n.get(k, 0.0)) for k in keys), 4)


def _normalise(d: Dict[str, float]) -> Dict[str, float]:
    total = float(sum(v for v in d.values() if v > 0))
    if total <= 0:
        return {}
    return {k: v / total for k, v in d.items() if v > 0}


def jaccard(a: Iterable[Hashable], b: Iterable[Hashable]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def tokens(text: str) -> List[str]:
    return [t.lower() for t in _WORD.findall(text or "")]


def shingles(text: str, k: int = 3) -> set:
    toks = tokens(text)
    if len(toks) < k:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def surface_similarity(a: str, b: str) -> float:
    """Word-sequence similarity (0..1): ``difflib.SequenceMatcher`` ratio over
    lower-cased word tokens (Ratcliff/Obershelp: 2·matches / total tokens).

    Unlike shingle overlap it stays high when only one or two numbers are
    swapped in otherwise identical wording, which is what copy detection needs.
    """
    ta, tb = tokens(a), tokens(b)
    if not ta and not tb:
        return 1.0
    return difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio()


def edit_distance(a: Sequence[Hashable], b: Sequence[Hashable]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def normalized_edit_similarity(a: Sequence[Hashable], b: Sequence[Hashable]) -> float:
    if not a and not b:
        return 1.0
    return 1.0 - edit_distance(a, b) / max(len(a), len(b))


def evidence_level(n_papers: int) -> str:
    """Categorical description of how much evidence supports a blueprint."""
    if n_papers <= 1:
        return "insufficient"
    if n_papers <= 3:
        return "limited"
    if n_papers <= 9:
        return "moderate"
    return "substantial"


def largest_remainder(total: int, weights: Dict[str, float]) -> Dict[str, int]:
    """Apportion an integer total according to weights (Hamilton method)."""
    norm = _normalise(weights)
    if not norm:
        return {k: 0 for k in weights}
    raw = {k: total * v for k, v in norm.items()}
    floors = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(floors.values())
    order = sorted(raw, key=lambda k: (-(raw[k] - floors[k]), k))
    for k in order[:remainder]:
        floors[k] += 1
    for k in weights:
        floors.setdefault(k, 0)
    return floors
