"""Validation pipeline for mutation candidates and question banks.

Aggregate state per item:
    any FAIL                              → FAIL
    else any REVIEW_REQUIRED/NOT_VERIFIED → REVIEW_REQUIRED
    else                                  → PASS
INFO findings never change the state. Only PASS items enter the approved
pool; REVIEW_REQUIRED items are kept but visibly flagged; FAIL items are
rejected.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import SCHEMA_VERSION
from ..extraction.normalize import normalize_question
from ..genome.builder import check_genome, finalize_genome
from ..models.constants import FAIL, NOT_VERIFIED, PASS, REVIEW_REQUIRED
from ..models.schema import validate
from ..mutation.distance import distance_profile, within_mode
from ..mutation.diversity import SURFACE_DUPLICATE, structural_signature
from ..mutation.operators import REGISTRY
from ..mutation.properties import difficulty_delta, full_text, property_unchanged
from ..utilities.ids import stable_id
from ..utilities.io import InputError
from ..utilities.stats import surface_similarity
from .checks import INFO, answer_checks, chk, constraint_checks, numeric_checks, structural_checks

SOURCE_COPY_LIMIT = 0.85


def aggregate(checks: List[Dict[str, Any]]) -> str:
    statuses = {c["status"] for c in checks}
    if FAIL in statuses:
        return FAIL
    if REVIEW_REQUIRED in statuses or NOT_VERIFIED in statuses:
        return REVIEW_REQUIRED
    return PASS


def _summary(checks: List[Dict[str, Any]], state: str) -> str:
    bad = [c for c in checks if c["status"] in (FAIL, REVIEW_REQUIRED, NOT_VERIFIED)]
    if not bad:
        return "all checks passed"
    first = [c for c in bad if c["status"] == FAIL] or bad
    return f"{state}: " + "; ".join(f"{c['check']}: {c['message']}" for c in first[:3])


def validate_question(q: Dict[str, Any], verification: Optional[Dict[str, Any]] = None, judgements: Optional[Dict[str, bool]] = None) -> List[Dict[str, Any]]:
    checks = [chk("schema", "question_schema", PASS, "question schema valid")]
    errors = validate(q, "question")
    if errors:
        return [chk("schema", "question_schema", FAIL, "; ".join(errors[:5]))]
    checks += structural_checks(q)
    checks += constraint_checks(q)
    checks += numeric_checks(q, verification)
    checks += answer_checks(q, verification, judgements)
    return checks


def _invariant_checks(spec, pq, pg, cq, cg, judgements) -> List[Dict[str, Any]]:
    out = []
    for prop in spec["preserve"]:
        unchanged = property_unchanged(prop, pq, pg, cq, cg)
        if unchanged is True:
            out.append(chk("invariants", f"preserve:{prop}", PASS, f"{prop} preserved"))
        elif unchanged is False:
            out.append(chk("invariants", f"preserve:{prop}", FAIL, f"{prop} was supposed to be preserved but changed"))
        elif prop in judgements:
            out.append(
                chk("invariants", f"preserve:{prop}", PASS if judgements[prop] else FAIL, f"{prop} {'preserved' if judgements[prop] else 'not preserved'} (agent judgement)", "model_assisted")
            )
        else:
            out.append(chk("invariants", f"preserve:{prop}", NOT_VERIFIED, f"{prop} needs a semantic judgement"))
    for prop in spec["must_change"]:
        if prop == "difficulty_features":
            delta = difficulty_delta(pg, cg)
            direction = spec["parameters"].get("direction", "up")
            if delta is None:
                out.append(chk("invariants", "change:difficulty_features", NOT_VERIFIED, "difficulty features unavailable"))
            elif (direction == "up" and delta >= 1) or (direction == "down" and delta <= -1):
                out.append(chk("invariants", "change:difficulty_features", PASS, f"heuristic difficulty points changed by {delta:+d} ({direction})"))
            else:
                out.append(chk("invariants", "change:difficulty_features", FAIL, f"difficulty points changed by {delta:+d}; expected a move {direction}"))
            continue
        unchanged = property_unchanged(prop, pq, pg, cq, cg)
        if unchanged is False:
            out.append(chk("invariants", f"change:{prop}", PASS, f"{prop} changed as required"))
        elif unchanged is True:
            out.append(chk("invariants", f"change:{prop}", FAIL, f"mutation not applied: {prop} is unchanged"))
        elif prop in judgements:
            changed = not judgements[prop]
            out.append(chk("invariants", f"change:{prop}", PASS if changed else FAIL, f"{prop} {'changed' if changed else 'unchanged'} (agent judgement)", "model_assisted"))
        else:
            out.append(chk("invariants", f"change:{prop}", NOT_VERIFIED, f"whether {prop} changed needs a semantic judgement"))
    for prop in spec.get("required_judgements", []):
        if prop in ("context",) and any(c["check"].endswith(f":{prop}") for c in out):
            continue
        if prop in judgements:
            out.append(chk("invariants", f"judgement:{prop}", PASS if judgements[prop] else FAIL, f"agent judgement on {prop}", "model_assisted"))
        else:
            out.append(chk("invariants", f"judgement:{prop}", NOT_VERIFIED, f"no agent judgement supplied for {prop}"))
    return out


def validate_candidates(
    candidates: Sequence[Dict[str, Any]],
    plan: Dict[str, Any],
    bank: Dict[str, Any],
    genomes: Sequence[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Validate candidates against their specs. Returns ``(report, pool)``.

    ``bank``/``genomes`` must contain every parent (source questions and any
    previously accepted generated questions used as parents).
    """
    specs = {s["spec_id"]: s for s in plan["specs"]}
    q_by_id = {q["id"]: q for q in bank["questions"]}
    g_by_q = {g["question_id"]: g for g in genomes}
    source_texts = [(q["id"], full_text(q)) for q in bank["questions"] if q["source"]["origin"] != "generated"]
    results: List[Dict[str, Any]] = []
    accepted_q: List[Dict[str, Any]] = []
    accepted_g: List[Dict[str, Any]] = []
    seen_ids = set(q_by_id)
    kept: List[Tuple[str, str, str]] = []  # (question id, text, signature)

    for cand in sorted(candidates, key=lambda c: str(c.get("candidate_id"))):
        checks: List[Dict[str, Any]] = []
        cid = str(cand.get("candidate_id", "?"))
        errors = validate(cand, "candidate")
        if errors:
            results.append({"candidate_id": cid, "state": FAIL, "summary": "candidate schema invalid", "checks": [chk("schema", "candidate_schema", FAIL, "; ".join(errors[:5]))]})
            continue
        spec = specs.get(cand["spec_id"])
        if spec is None:
            results.append({"candidate_id": cid, "state": FAIL, "summary": "unknown spec", "checks": [chk("lineage", "spec_exists", FAIL, f"spec {cand['spec_id']} is not in the plan")]})
            continue
        lineage_ok = True
        if cand["parent_id"] != spec["parent_id"]:
            checks.append(chk("lineage", "parent_matches_spec", FAIL, f"candidate parent {cand['parent_id']} ≠ spec parent {spec['parent_id']}"))
            lineage_ok = False
        if cand["operator"] != spec["operator"]:
            checks.append(chk("lineage", "operator_matches_spec", FAIL, f"candidate operator {cand['operator']} ≠ spec operator {spec['operator']}"))
            lineage_ok = False
        if cand["operator"] not in REGISTRY:
            checks.append(chk("lineage", "operator_registered", FAIL, f"unknown operator {cand['operator']}"))
            lineage_ok = False
        pq, pg = q_by_id.get(spec["parent_id"]), g_by_q.get(spec["parent_id"])
        if pq is None or pg is None:
            checks.append(chk("lineage", "parent_exists", FAIL, f"parent {spec['parent_id']} or its genome is missing"))
            lineage_ok = False
        if lineage_ok:
            checks.append(chk("lineage", "lineage_consistent", PASS, f"{spec['operator']} of {spec['parent_id']}"))

        # Normalize the candidate question (also enforces the question schema).
        raw_q = copy.deepcopy(cand["question"])
        raw_q.setdefault("source", {})
        raw_q["source"] = {**raw_q["source"], "origin": "generated", "document": None}
        root = ((pq or {}).get("lineage") or {}).get("root_id") or spec["parent_id"]
        raw_q["lineage"] = {
            "parent_id": spec["parent_id"],
            "root_id": root,
            "operator": spec["operator"],
            "spec_id": spec["spec_id"],
            "candidate_id": cid,
            "generation": spec.get("generation", 1),
            "mutation_parameters": spec["parameters"],
            "preserved": spec["preserve"],
            "changed": spec["must_change"],
            "created": None,
        }
        claimed_lineage = cand["question"].get("lineage")
        if claimed_lineage and claimed_lineage.get("parent_id") not in (None, spec["parent_id"]):
            checks.append(chk("lineage", "claimed_lineage", FAIL, "candidate's own lineage contradicts the spec"))
        try:
            cq, q_issues = normalize_question(raw_q, origin="generated", default_provenance="inferred")
        except InputError as exc:
            checks.append(chk("schema", "question_schema", FAIL, str(exc)))
            results.append({"candidate_id": cid, "state": FAIL, "summary": _summary(checks, FAIL), "checks": checks})
            continue
        if cq["id"] in seen_ids:
            checks.append(chk("schema", "unique_id", FAIL, f"question id {cq['id']} already exists"))

        cg = copy.deepcopy(cand["genome"])
        cg["question_id"] = cq["id"]
        cg["parent_question_id"] = spec["parent_id"]
        cg.setdefault("lineage", [])
        cg["lineage"] = list((pg or {}).get("lineage") or []) + [{"question_id": spec["parent_id"], "operator": spec["operator"], "spec_id": spec["spec_id"]}]
        cg.setdefault("validation", {})
        verification = cand.get("verification")
        if isinstance(cg.get("assessment"), dict) and not cg["assessment"].get("answer_unit") and (verification or {}).get("claimed_unit"):
            cg["assessment"]["answer_unit"] = verification["claimed_unit"]
        g_errors = validate(cg, "genome")
        if g_errors:
            checks.append(chk("schema", "genome_schema", FAIL, "; ".join(g_errors[:5])))
            results.append({"candidate_id": cid, "question_id": cq["id"], "state": FAIL, "summary": _summary(checks, FAIL), "checks": checks})
            continue
        cg = finalize_genome(cg)
        graph_errors = check_genome(cg)
        if graph_errors:
            checks.append(chk("schema", "reasoning_graph", FAIL, "; ".join(graph_errors[:3])))
        else:
            checks.append(chk("schema", "genome_schema", PASS, "genome schema and reasoning graph valid"))

        judgements = {j["property"]: j["preserved"] for j in cand.get("invariant_judgements") or []}
        verification = cand.get("verification")
        checks += validate_question(cq, verification, judgements)[1:]  # schema already enforced
        for issue in q_issues:
            if "part marks sum" in issue:
                checks.append(chk("structural", "normalization", FAIL, issue))

        if pq is not None and pg is not None and lineage_ok:
            checks += _invariant_checks(spec, pq, pg, cq, cg, judgements)
            profile = distance_profile(pq, pg, cq, cg, judgements)
            limit_msg = within_mode(profile, spec["mode"])
            if limit_msg and spec["operator"] != "fusion":
                checks.append(chk("distance", "mode_limit", REVIEW_REQUIRED, limit_msg))
            if profile["novelty"] == "near_duplicate":
                checks.append(chk("distance", "novelty", FAIL, "candidate is a near-duplicate of its parent"))
            else:
                checks.append(chk("distance", "novelty", PASS, profile["novelty"]))
        else:
            profile = None

        text = full_text(cq)
        worst = max(((sid, surface_similarity(text, st)) for sid, st in source_texts), key=lambda x: x[1], default=(None, 0.0))
        if worst[1] >= SOURCE_COPY_LIMIT:
            checks.append(chk("duplicates", "source_copy", FAIL, f"near-verbatim copy of source question {worst[0]} (surface similarity {worst[1]:.2f})"))
        sig = structural_signature(cq, cg)
        for kid, ktext, ksig in kept:
            sim = surface_similarity(text, ktext)
            if sim >= SURFACE_DUPLICATE or sig == ksig:
                checks.append(chk("duplicates", "candidate_duplicate", REVIEW_REQUIRED, f"duplicates accepted candidate {kid}"))
                break

        state = aggregate(checks)
        model_assisted = any(c["method"] == "model_assisted" for c in checks)
        numeric_verified = any(c["check"] == "recompute" and c["status"] == PASS for c in checks)
        cq["validation"] = {"state": state, "summary": _summary(checks, state), "model_assisted": model_assisted, "numeric_verified": numeric_verified}
        cq["review_status"] = "needs_review" if state == REVIEW_REQUIRED else cq.get("review_status", "unreviewed")
        if verification:
            cq.setdefault("extensions", {})["verification"] = verification
        cg["validation"]["answer_validation"] = PASS if numeric_verified else (REVIEW_REQUIRED if state != FAIL else FAIL)
        cg["validation"]["solvability"] = PASS if numeric_verified else NOT_VERIFIED
        if verification and verification.get("answer_uniqueness"):
            cg["validation"]["uniqueness"] = verification["answer_uniqueness"]
        results.append(
            {
                "candidate_id": cid,
                "question_id": cq["id"],
                "spec_id": spec["spec_id"],
                "parent_id": spec["parent_id"],
                "operator": spec["operator"],
                "state": state,
                "summary": cq["validation"]["summary"],
                "model_assisted": model_assisted,
                "numeric_verified": numeric_verified,
                "distance": profile,
                "checks": checks,
            }
        )
        if state in (PASS, REVIEW_REQUIRED) and cq["id"] not in seen_ids:
            seen_ids.add(cq["id"])
            kept.append((cq["id"], text, sig))
            accepted_q.append(cq)
            accepted_g.append(cg)

    counts = {s: sum(1 for r in results if r["state"] == s) for s in (PASS, REVIEW_REQUIRED, FAIL)}
    report = {
        "schema_version": SCHEMA_VERSION,
        "report_id": stable_id("validation", plan.get("plan_id"), [r["candidate_id"] for r in results], [r["state"] for r in results]),
        "plan_id": plan.get("plan_id"),
        "summary": {"candidates": len(results), **counts},
        "results": results,
        "assurance_note": (
            "PASS means every applicable deterministic check passed and every required semantic judgement was supplied "
            "and affirmative. Checks marked model_assisted rely on the agent's judgement, not on independent verification."
        ),
    }
    pool = {
        "schema_version": SCHEMA_VERSION,
        "bank_id": stable_id("pool", [q["id"] for q in accepted_q]),
        "title": "Validated mutation pool",
        "source_documents": [],
        "questions": accepted_q,
        "normalization_report": {"question_count": len(accepted_q), "issues": [], "missing_marks": [], "security_flagged": []},
        "extensions": {"genomes": accepted_g, "validation_report_id": report["report_id"]},
    }
    return report, pool


def validate_bank(bank: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a question bank in place (no mutation context)."""
    results = []
    for q in bank["questions"]:
        verification = (q.get("extensions") or {}).get("verification")
        checks = validate_question(q, verification)
        state = aggregate(checks)
        results.append({"question_id": q["id"], "state": state, "summary": _summary(checks, state), "checks": checks})
    counts = {s: sum(1 for r in results if r["state"] == s) for s in (PASS, REVIEW_REQUIRED, FAIL)}
    return {
        "schema_version": SCHEMA_VERSION,
        "report_id": stable_id("bankcheck", bank.get("bank_id"), [r["state"] for r in results]),
        "summary": {"questions": len(results), **counts},
        "results": results,
    }


def apply_states(bank: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``bank`` with validation states written into questions."""
    out = copy.deepcopy(bank)
    states = {r["question_id"]: r for r in report["results"]}
    for q in out["questions"]:
        r = states.get(q["id"])
        if r:
            q["validation"] = {
                "state": r["state"],
                "summary": r["summary"],
                "model_assisted": any(c["method"] == "model_assisted" for c in r["checks"]),
                "numeric_verified": any(c["check"] == "recompute" and c["status"] == PASS for c in r["checks"]),
            }
    return out


__all__ = ["validate_candidates", "validate_bank", "validate_question", "aggregate", "apply_states", "INFO"]
