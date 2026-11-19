"""Exam compiler: bounded branch-and-bound over section combinations.

Algorithm
---------
1. Filter the pool by hard eligibility rules (validation state, origin,
   topic allow/deny lists, marks known).
2. For each section, enumerate question combinations whose marks sum
   *exactly* to the section's marks and satisfy count and per-family limits
   (depth-first, items in a seeded deterministic order; at most
   ``MAX_COMBOS_PER_SECTION`` combinations per section).
3. Combine one combination per section depth-first, rejecting overlaps,
   per-family excess, wrong total question count and missing required
   topics/types. Each complete exam is scored with the soft objective;
   the lowest score wins (first found wins ties).
4. Search stops after ``search_budget`` nodes. The result reports whether
   the search was exhaustive. Only an exhaustive search is "optimal" — and
   only with respect to this objective, never educationally.

Soft objective (lower is better)::

    cost = w_topic·TV(topic) + w_cognitive·TV(cognitive) + w_difficulty·TV(band)
         + w_type·TV(question_type) + w_family·(repeated families / questions)
         + w_count·|n − n_target| / n_target

where n_target is the blueprint's median question count scaled by
total_marks / blueprint total marks (absent without Exam DNA or when
question_count is fixed by the config).

where TV is total-variation distance between mark-weighted distributions of
the exam and the targets (Exam DNA or config). Absent targets contribute 0.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import SCHEMA_VERSION
from ..fingerprint.analyzer import question_difficulty
from ..models.constants import DIFFICULTY_BANDS, PASS, REVIEW_REQUIRED
from ..models.schema import validate
from ..utilities.ids import digest, stable_id
from ..utilities.stats import largest_remainder, proportions, total_variation

MAX_COMBOS_PER_SECTION = 4000
DEFAULT_WEIGHTS = {"topic": 1.0, "cognitive": 0.5, "difficulty": 0.75, "question_type": 0.5, "family_repeat": 0.5, "question_count": 0.5}
DEFAULT_INSTRUCTIONS = {
    "en": ["Answer all questions.", "Show your working for calculation questions.", "Marks for each question are shown in brackets."],
    "tr": ["Tüm soruları cevaplayınız.", "Hesaplama sorularında işlemlerinizi gösteriniz.", "Her sorunun puanı köşeli parantez içinde verilmiştir."],
}


class CompilationInfeasible(Exception):
    def __init__(self, diagnosis: Dict[str, Any]):
        self.diagnosis = diagnosis
        super().__init__(diagnosis.get("message", "no exam satisfies the constraints"))


def shift_bands(dist: Dict[str, float], shift: int) -> Dict[str, float]:
    """Move probability mass ``shift`` bands up (positive) or down (negative)."""
    out = {b: 0.0 for b in DIFFICULTY_BANDS}
    for band, p in dist.items():
        if band not in out:
            continue
        idx = min(max(DIFFICULTY_BANDS.index(band) + shift, 0), len(DIFFICULTY_BANDS) - 1)
        out[DIFFICULTY_BANDS[idx]] += p
    return {k: round(v, 4) for k, v in out.items() if v > 0}


def _item(q: Dict[str, Any], genome: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    diff = question_difficulty(q, genome)
    return {
        "id": q["id"],
        "marks": q["marks"],
        "topic": q.get("topic"),
        "type": q.get("question_type"),
        "cognitive": q.get("cognitive_level"),
        "band": diff["band"],
        "difficulty_points": diff["points"],
        "family": (q.get("lineage") or {}).get("root_id") or q["id"],
        "section": q.get("section"),
        "state": (q.get("validation") or {}).get("state", "NOT_VERIFIED"),
    }


def _fits(item: Dict[str, Any], section: Dict[str, Any]) -> bool:
    allowed = section.get("allowed_types") or []
    if allowed and item["type"] not in allowed:
        return False
    src = section.get("source_sections") or []
    if src and item["section"] is not None and item["section"] not in src:
        return False
    return True


def _derive_sections(config: Dict[str, Any], dna: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    notes = []
    if config.get("sections"):
        return [dict(s) for s in config["sections"]], notes
    total = config["total_marks"]
    if dna:
        shares = {k: v for k, v in dna["structural_constraints"]["section_mark_share"].items() if v}
        if shares:
            marks = largest_remainder(total, shares)
            sections = []
            for label in dna["structural_constraints"]["section_order"]:
                if marks.get(label):
                    sdef = next(s for s in dna["sections"] if s["label"] == label)
                    sections.append(
                        {
                            "label": label if label != "(none)" else "A",
                            "title": None,
                            "marks": marks[label],
                            "allowed_types": sorted(sdef["question_types"].keys()),
                            "source_sections": [label] if label != "(none)" else [],
                        }
                    )
            notes.append(f"Sections derived from Exam DNA mark shares and scaled to {total} marks (largest-remainder rounding).")
            return sections, notes
    notes.append("No sections supplied and no Exam DNA: using a single section.")
    return [{"label": "A", "title": None, "marks": total}], notes


def _subset_sums(marks: Sequence[int], limit: int) -> set:
    sums = {0}
    for m in marks:
        sums |= {s + m for s in sums if s + m <= limit}
    return sums


def _distribution(items: Sequence[Dict[str, Any]], key: str) -> Dict[str, float]:
    d: Dict[str, float] = defaultdict(float)
    for it in items:
        if it.get(key):
            d[it[key]] += it["marks"]
    return dict(d)


def compile_exam(
    pool: Dict[str, Any],
    config: Dict[str, Any],
    dna: Optional[Dict[str, Any]] = None,
    genomes: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    errors = validate(config, "compile_config")
    if errors:
        raise ValueError("invalid compile config: " + "; ".join(errors[:5]))
    seed = int(config.get("seed", 0))
    weights = {**DEFAULT_WEIGHTS, **(config.get("weights") or {})}
    budget = int(config.get("search_budget", 200000))
    max_family = int(config.get("max_per_family", 1))
    language = config.get("language", "en")

    all_genomes = list(genomes or []) + list((pool.get("extensions") or {}).get("genomes") or [])
    g_by_q = {g["question_id"]: g for g in all_genomes}
    q_by_id = {q["id"]: q for q in pool["questions"]}

    # 1. eligibility
    excluded: Dict[str, List[str]] = defaultdict(list)
    eligible: List[Dict[str, Any]] = []
    allowed_topics = {t.lower() for t in config.get("allowed_topics") or []}
    excluded_topics = {t.lower() for t in config.get("excluded_topics") or []}
    for q in pool["questions"]:
        state = (q.get("validation") or {}).get("state", "NOT_VERIFIED")
        topic = (q.get("topic") or "").lower()
        if q["source"]["origin"] != "generated" and not config.get("include_source_questions", False):
            excluded["source_question_not_allowed"].append(q["id"])
        elif state == REVIEW_REQUIRED and not config.get("include_review_required", False):
            excluded["review_required"].append(q["id"])
        elif state not in (PASS, REVIEW_REQUIRED):
            excluded[f"state_{state}"].append(q["id"])
        elif not q.get("marks"):
            excluded["no_marks"].append(q["id"])
        elif topic in excluded_topics:
            excluded["excluded_topic"].append(q["id"])
        elif allowed_topics and topic not in allowed_topics:
            excluded["topic_not_allowed"].append(q["id"])
        else:
            eligible.append(_item(q, g_by_q.get(q["id"])))

    sections, notes = _derive_sections(config, dna)
    total = config["total_marks"]
    section_total = sum(s["marks"] for s in sections)

    # targets
    targets: Dict[str, Dict[str, float]] = {}
    if dna:
        dist = dna["distributions"]
        topic_t = dist["topic"]["share_by_marks"]
        if allowed_topics:
            topic_t = {k: v for k, v in topic_t.items() if k.lower() in allowed_topics}
        topic_t = {k: v for k, v in topic_t.items() if k.lower() not in excluded_topics}
        targets["topic"] = topic_t
        targets["cognitive"] = dist["cognitive_level"]["share_by_marks"]
        targets["question_type"] = dist["question_type"]["share_by_marks"]
        targets["difficulty"] = dist["difficulty_band"]["share_by_marks"]
    if config.get("difficulty_target"):
        targets["difficulty"] = dict(config["difficulty_target"])
    if config.get("difficulty_shift") and targets.get("difficulty"):
        targets["difficulty"] = shift_bands(targets["difficulty"], int(config["difficulty_shift"]))
        notes.append(f"Difficulty target shifted by {config['difficulty_shift']:+d} band(s) (heuristic bands).")
    elif config.get("difficulty_shift"):
        targets["difficulty"] = shift_bands({"standard": 1.0}, int(config["difficulty_shift"]))
        notes.append("No difficulty baseline available; shift applied to an all-'standard' baseline.")

    count_target: Optional[float] = None
    if dna and not config.get("question_count"):
        sc = dna["structural_constraints"]
        if sc.get("target_question_count") and sc.get("target_total_marks"):
            count_target = round(sc["target_question_count"] * total / sc["target_total_marks"], 2)
            targets["question_count"] = {"n": count_target}

    def cost(items: Sequence[Dict[str, Any]]) -> Tuple[float, Dict[str, float]]:
        terms = {}
        for name, key in (("topic", "topic"), ("cognitive", "cognitive"), ("difficulty", "band"), ("question_type", "type")):
            terms[name] = total_variation(_distribution(items, key), targets[name]) if targets.get(name) else 0.0
        fam = Counter(it["family"] for it in items)
        terms["family_repeat"] = round(sum(c - 1 for c in fam.values()) / max(len(items), 1), 4)
        terms["question_count"] = round(abs(len(items) - count_target) / count_target, 4) if count_target else 0.0
        return round(sum(weights[k] * v for k, v in terms.items()), 6), terms

    def order_key(it):
        return digest(seed, it["id"])

    # 2. per-section combinations
    def diagnose(message: str, extra: Optional[Dict[str, Any]] = None) -> CompilationInfeasible:
        sec_diag = []
        for s in sections:
            fit = [it for it in eligible if _fits(it, s)]
            sums = _subset_sums([it["marks"] for it in fit], s["marks"] * 2)
            below = max((x for x in sums if x <= s["marks"]), default=0)
            above = min((x for x in sums if x >= s["marks"]), default=None)
            sec_diag.append(
                {
                    "label": s["label"],
                    "target_marks": s["marks"],
                    "eligible_questions": len(fit),
                    "eligible_marks": sum(it["marks"] for it in fit),
                    "target_reachable": s["marks"] in sums,
                    "nearest_reachable_below": below,
                    "nearest_reachable_above": above,
                    "types_available": dict(Counter(it["type"] for it in fit)),
                }
            )
        available_topics = {(it["topic"] or "").lower() for it in eligible}
        available_types = {it["type"] for it in eligible}
        missing_topics = [t for t in config.get("required_topics") or [] if t.lower() not in available_topics]
        missing_types = [t for t in config.get("required_types") or [] if t not in available_types]
        suggestions = []
        for d in sec_diag:
            if not d["target_reachable"]:
                alt = [x for x in (d["nearest_reachable_below"], d["nearest_reachable_above"]) if x]
                suggestions.append(f"Section {d['label']}: {d['target_marks']} marks cannot be formed exactly; reachable nearby totals: {alt}.")
        if excluded.get("review_required"):
            suggestions.append(f"{len(excluded['review_required'])} REVIEW_REQUIRED question(s) could be allowed with include_review_required (they stay flagged).")
        if missing_topics:
            suggestions.append(f"Generate validated questions for required topic(s): {', '.join(missing_topics)}, or drop them from required_topics.")
        if missing_types:
            suggestions.append(f"Generate validated questions of type(s): {', '.join(missing_types)}, or drop them from required_types.")
        pool_marks = sum(it["marks"] for it in eligible)
        if pool_marks < total:
            suggestions.append(f"Eligible pool holds only {pool_marks} marks; reduce total_marks to at most {pool_marks} or generate more questions.")
        if max_family == 1:
            suggestions.append("Raising max_per_family allows several variants of the same source question.")
        diag = {
            "message": message,
            "total_marks": total,
            "eligible_questions": len(eligible),
            "eligible_marks": pool_marks,
            "excluded": {k: len(v) for k, v in excluded.items()},
            "sections": sec_diag,
            "missing_required_topics": missing_topics,
            "missing_required_types": missing_types,
            "suggestions": suggestions,
        }
        if extra:
            diag.update(extra)
        return CompilationInfeasible(diag)

    if section_total != total:
        raise diagnose(f"section marks sum to {section_total} but total_marks is {total}", {"conflict": "section_marks_vs_total"})
    if config.get("question_count") and any(s.get("question_count") for s in sections):
        sc = sum(s.get("question_count") or 0 for s in sections)
        if all(s.get("question_count") for s in sections) and sc != config["question_count"]:
            raise diagnose(f"section question counts sum to {sc} but question_count is {config['question_count']}", {"conflict": "section_counts_vs_question_count"})

    truncated = False
    section_combos: List[List[Tuple[float, Tuple[str, ...]]]] = []
    by_id = {it["id"]: it for it in eligible}
    for s in sections:
        fit = sorted((it for it in eligible if _fits(it, s)), key=order_key)
        target = s["marks"]
        min_q = s.get("question_count") or s.get("min_questions") or 1
        max_q = s.get("question_count") or s.get("max_questions") or len(fit)
        suffix = [0] * (len(fit) + 1)
        for i in range(len(fit) - 1, -1, -1):
            suffix[i] = suffix[i + 1] + fit[i]["marks"]
        combos: List[Tuple[str, ...]] = []
        stack: List[str] = []
        fam: Counter = Counter()

        def dfs(i: int, remaining: int) -> None:
            nonlocal truncated
            if len(combos) >= MAX_COMBOS_PER_SECTION:
                truncated = True
                return
            if remaining == 0:
                if min_q <= len(stack) <= max_q:
                    combos.append(tuple(stack))
                return
            if i >= len(fit) or suffix[i] < remaining or len(stack) >= max_q:
                return
            it = fit[i]
            if it["marks"] <= remaining and fam[it["family"]] < max_family:
                stack.append(it["id"])
                fam[it["family"]] += 1
                dfs(i + 1, remaining - it["marks"])
                fam[it["family"]] -= 1
                stack.pop()
            dfs(i + 1, remaining)

        dfs(0, target)
        if not combos:
            raise diagnose(f"section {s['label']} cannot be filled with exactly {target} marks from eligible questions")
        scored = sorted(((cost([by_id[x] for x in c])[0], c) for c in combos), key=lambda t: t[0])
        section_combos.append(scored)

    # 3. combine sections
    best: Dict[str, Any] = {"cost": None, "selection": None}
    nodes = 0
    budget_hit = False
    req_topics = {t.lower() for t in config.get("required_topics") or []}
    req_types = set(config.get("required_types") or [])
    q_count = config.get("question_count")

    def combine(k: int, chosen: List[Tuple[str, ...]], used: set, fam: Counter) -> None:
        nonlocal nodes, budget_hit
        if budget_hit:
            return
        nodes += 1
        if nodes > budget:
            budget_hit = True
            return
        if k == len(sections):
            ids = [i for c in chosen for i in c]
            if q_count and len(ids) != q_count:
                return
            items = [by_id[i] for i in ids]
            if req_topics - {(it["topic"] or "").lower() for it in items}:
                return
            if req_types - {it["type"] for it in items}:
                return
            c, _ = cost(items)
            if best["cost"] is None or c < best["cost"]:
                best["cost"], best["selection"] = c, [list(x) for x in chosen]
            return
        for _, combo in section_combos[k]:
            if any(i in used for i in combo):
                continue
            fam2 = fam.copy()
            ok = True
            for i in combo:
                fam2[by_id[i]["family"]] += 1
                if fam2[by_id[i]["family"]] > max_family:
                    ok = False
                    break
            if not ok:
                continue
            combine(k + 1, chosen + [combo], used | set(combo), fam2)
            if budget_hit:
                return

    combine(0, [], set(), Counter())
    if best["selection"] is None:
        raise diagnose(
            "no combination of section selections satisfies all hard constraints"
            + (" within the search budget" if budget_hit else ""),
            {"search_budget_exhausted": budget_hit},
        )

    # 4. assemble exam
    number = 0
    out_sections = []
    selected_items = []
    for s, ids in zip(sections, best["selection"]):
        ids = sorted(ids, key=lambda i: (by_id[i]["marks"], i))  # ascending marks within section
        qs = []
        for qid in ids:
            number += 1
            q = q_by_id[qid]
            selected_items.append(by_id[qid])
            qs.append(
                {
                    "number": number,
                    "id": qid,
                    "marks": q["marks"],
                    "validation_state": by_id[qid]["state"],
                    "difficulty_band": by_id[qid]["band"],
                    "lineage": q.get("lineage"),
                    "question": q,
                }
            )
        out_sections.append(
            {"label": s["label"], "title": s.get("title"), "instructions": s.get("instructions"), "marks": s["marks"], "questions": qs}
        )
    final_cost, terms = cost(selected_items)
    actual = {
        "topic": proportions(_distribution(selected_items, "topic")),
        "cognitive": proportions(_distribution(selected_items, "cognitive")),
        "question_type": proportions(_distribution(selected_items, "type")),
        "difficulty": proportions(_distribution(selected_items, "band")),
    }
    exhaustive = not truncated and not budget_hit
    selected_ids = [q["id"] for s in out_sections for q in s["questions"]]
    exam = {
        "schema_version": SCHEMA_VERSION,
        "exam_id": stable_id("exam", seed, selected_ids, config),
        "title": config.get("title") or "Practice Examination",
        "subject": config.get("subject") or next(iter(((dna or {}).get("source_set") or {}).get("subjects") or {}), None),
        "language": language,
        "total_marks": total,
        "question_count": len(selected_ids),
        "time_minutes": config.get("time_minutes"),
        "instructions": config.get("instructions") or DEFAULT_INSTRUCTIONS.get(language, DEFAULT_INSTRUCTIONS["en"]),
        "seed": seed,
        "config": config,
        "sections": out_sections,
        "properties": {
            "actual_mark_shares": actual,
            "targets": targets,
            "deviation_total_variation": terms,
            "objective": final_cost,
            "review_required_questions": [i for i in selected_ids if by_id[i]["state"] == REVIEW_REQUIRED],
            "families_used": dict(Counter(it["family"] for it in selected_items)),
        },
        "solver": {
            "algorithm": "bounded depth-first branch-and-bound over exact-sum section combinations",
            "nodes_explored": nodes,
            "search_budget": budget,
            "combinations_per_section": [len(c) for c in section_combos],
            "section_enumeration_truncated": truncated,
            "exhaustive": exhaustive,
            "optimality": "best possible under the stated objective" if exhaustive else "best found within limits; optimality not established",
            "notes": notes,
        },
        "provenance": {"pool_id": pool.get("bank_id"), "dna_profile_id": (dna or {}).get("profile_id"), "excluded": {k: len(v) for k, v in excluded.items()}},
    }
    return exam
