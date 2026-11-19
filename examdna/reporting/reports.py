"""Human-readable analysis reports. Every number comes from the input JSON."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..mutation.lineage import render_tree


def _pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _dist_table(title: str, dist: Dict[str, Any]) -> List[str]:
    counts = dist.get("counts") or {}
    if not counts:
        return [f"### {title}", "", "_No data._", ""]
    by_marks = dist.get("share_by_marks") or {}
    lines = [f"### {title}", "", "| Category | Questions | Share (count) | Share (marks) |", "| --- | --- | --- | --- |"]
    for k, n in counts.items():
        lines.append(f"| {k} | {n} | {_pct(dist['share_by_count'].get(k))} | {_pct(by_marks.get(k))} |")
    if dist.get("unclassified"):
        lines.append(f"| _(unclassified)_ | {len(dist['unclassified'])} | | |")
    lines.append("")
    return lines


def dna_report_markdown(dna: Dict[str, Any]) -> str:
    u = dna["uncertainty"]
    agg = dna["aggregate"]
    lines = [
        "# Exam DNA Report",
        "",
        f"Profile `{dna['profile_id']}` · {dna['source_set']['paper_count']} paper(s) · {dna['source_set']['question_count']} question(s)",
        "",
        f"**Evidence level: {u['evidence_level']}.**",
        "",
    ]
    for n in u["notes"]:
        lines.append(f"> ⚠ {n}")
    if u["notes"]:
        lines.append("")
    lines += ["## Source papers", "", "| Paper | Questions | Total marks | Sections |", "| --- | --- | --- | --- |"]
    for p in dna["papers"]:
        secs = ", ".join(f"{s['label']} ({s['marks']})" for s in p["sections"])
        lines.append(f"| {p['document']} | {p['question_count']} | {p['total_marks'] if p['total_marks'] is not None else 'incomplete'} | {secs} |")
    lines += ["", "## Aggregate structure", ""]

    def row(name, s):
        return f"| {name} | {s['n']} | {s['mean']} | {s['median']} | {s['min']} | {s['max']} |"

    lines += ["| Measure | n | Mean | Median | Min | Max |", "| --- | --- | --- | --- | --- | --- |"]
    lines += [row("Questions per paper", agg["questions_per_paper"]), row("Marks per paper", agg["marks_per_paper"]), row("Marks per question", agg["marks_per_question"]), ""]
    lines += ["## Sections", "", "| Section | In papers | Median marks | Mark share | Median questions | Types observed |", "| --- | --- | --- | --- | --- | --- |"]
    for s in dna["sections"]:
        types = ", ".join(f"{k}×{v}" for k, v in s["question_types"].items())
        lines.append(f"| {s['label']} | {s['papers_present']} | {s['marks']['median']} | {_pct(s['mark_share'])} | {s['question_count']['median']} | {types} |")
    lines += ["", "## Distributions", ""]
    d = dna["distributions"]
    lines += _dist_table("Topics", d["topic"])
    lines += _dist_table("Question types", d["question_type"])
    lines += _dist_table("Cognitive demand", d["cognitive_level"])
    lines += _dist_table("Heuristic difficulty band", d["difficulty_band"])
    lines += _dist_table("Learning objectives", d["learning_objective"])
    seq = dna["sequencing"]
    lines += ["## Sequencing", ""]
    for order, n in seq["section_orders"].items():
        lines.append(f"- Section order `{order}` in {n} paper(s)")
    for label, v in seq["marks_nondecreasing_within_section"].items():
        if v["papers_checked"]:
            lines.append(f"- Section {label}: marks non-decreasing in {v['papers_nondecreasing']}/{v['papers_checked']} paper(s)")
    if dna.get("concept_combinations"):
        lines += ["", "## Frequent concept combinations", ""]
        for c in dna["concept_combinations"][:10]:
            lines.append(f"- {' + '.join(c['concepts'])}: {c['count']} question(s)")
    sc = dna["structural_constraints"]
    lines += [
        "",
        "## Blueprint (derived)",
        "",
        f"- Target total marks: {sc['target_total_marks']} ({sc['basis']})",
        f"- Target question count: {sc['target_question_count']}",
        f"- Section mark shares: " + ", ".join(f"{k} {_pct(v)}" for k, v in sc["section_mark_share"].items()),
        "",
        "## Method notes",
        "",
        f"- Difficulty bands use the heuristic model `{dna['difficulty_model']['name']}` ({dna['difficulty_model']['status']}).",
        "- All shares are computed directly from the question bank; evidence lists in `exam_dna.json` name the supporting question IDs.",
        "- These are observed structural regularities of the supplied papers. They do not predict future examination content.",
        "",
    ]
    return "\n".join(lines)


def validation_summary_markdown(report: Dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Validation Summary",
        "",
        f"Report `{report['report_id']}`",
        "",
        "| Candidates | PASS | REVIEW_REQUIRED | FAIL |",
        "| --- | --- | --- | --- |",
        f"| {s.get('candidates', s.get('questions'))} | {s['PASS']} | {s['REVIEW_REQUIRED']} | {s['FAIL']} |",
        "",
    ]
    if report.get("assurance_note"):
        lines += [f"> {report['assurance_note']}", ""]
    lines += ["## Results", ""]
    for r in report["results"]:
        ident = r.get("candidate_id") or r.get("question_id")
        op = f" · {r['operator']} of `{r['parent_id']}`" if r.get("operator") else ""
        lines.append(f"### `{ident}` — **{r['state']}**{op}")
        lines.append("")
        if r.get("distance"):
            dims = r["distance"]["dimensions"]
            lines.append("Distance from parent: " + ", ".join(f"{k} {v['label']} ({v['distance']})" for k, v in dims.items()) + f" → **{r['distance']['novelty']}**")
            lines.append("")
        bad = [c for c in r["checks"] if c["status"] != "PASS"]
        if not bad:
            lines.append(f"All {len(r['checks'])} checks passed.")
        for c in bad:
            lines.append(f"- `{c['status']}` [{c['stage']}/{c['check']}, {c['method']}] {c['message']}")
        ma = sum(1 for c in r["checks"] if c["method"] == "model_assisted")
        if ma:
            lines.append(f"- _{ma} check(s) rely on agent judgement (model-assisted)._")
        lines.append("")
    return "\n".join(lines)


def lineage_report_markdown(lineage: Dict[str, Any], exam: Optional[Dict[str, Any]] = None) -> str:
    lines = ["# Question Lineage", ""]
    if not lineage["valid"]:
        lines += ["**Lineage errors:**", ""] + [f"- {e}" for e in lineage["errors"]] + [""]
    else:
        lines += ["Lineage integrity: all parents exist, generations are consistent, no cycles.", ""]
    if exam:
        lines += ["## Compiled exam", "", "| No. | Question | Operator | Parent | Root | Generation | Validation |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for sec in exam["sections"]:
            for item in sec["questions"]:
                lin = item.get("lineage") or {}
                lines.append(
                    f"| {item['number']} | `{item['id']}` | {lin.get('operator', '—')} | `{lin.get('parent_id', '—')}` | `{lin.get('root_id', item['id'])}` | {lin.get('generation', 0)} | {item['validation_state']} |"
                )
        lines.append("")
    lines += ["## Families", "", "```", render_tree(lineage).rstrip(), "```", ""]
    return "\n".join(lines)


def comparison_report_markdown(exam: Dict[str, Any], dna: Optional[Dict[str, Any]]) -> str:
    p = exam["properties"]
    lines = ["# Exam vs. Exam DNA", ""]
    if dna:
        lines += [f"Blueprint `{dna['profile_id']}` (evidence level: {dna['uncertainty']['evidence_level']})", ""]
        sc = dna["structural_constraints"]
        lines += [
            "| Property | Blueprint | Compiled exam |",
            "| --- | --- | --- |",
            f"| Total marks | {sc['target_total_marks']} (median of sources) | {exam['total_marks']} |",
            f"| Question count | {sc['target_question_count']} (median) | {exam['question_count']} |",
            f"| Sections | {', '.join(sc['section_order'])} | {', '.join(s['label'] + ' (' + str(s['marks']) + ')' for s in exam['sections'])} |",
            "",
        ]
    else:
        lines += ["_No Exam DNA profile supplied; targets come from the compile configuration only._", ""]
    for dim in ("topic", "cognitive", "question_type", "difficulty"):
        target = p["targets"].get(dim)
        actual = p["actual_mark_shares"].get(dim) or {}
        keys = sorted(set(actual) | set(target or {}))
        lines += [f"## {dim.replace('_', ' ').title()} (share of marks)", ""]
        if not keys:
            lines += ["_No data._", ""]
            continue
        lines += ["| Category | Target | Exam |", "| --- | --- | --- |"]
        for k in keys:
            lines.append(f"| {k} | {_pct((target or {}).get(k)) if target else '—'} | {_pct(actual.get(k))} |")
        tv = p["deviation_total_variation"].get(dim)
        lines += ["", f"Total-variation distance from target: **{tv}** (0 = identical distribution, 1 = disjoint)." if target else "No target for this dimension.", ""]
    lines += [
        "## Solver",
        "",
        f"- {exam['solver']['algorithm']}",
        f"- Nodes explored: {exam['solver']['nodes_explored']} (budget {exam['solver']['search_budget']})",
        f"- Exhaustive: {exam['solver']['exhaustive']} — {exam['solver']['optimality']}",
        f"- Objective value: {p['objective']}",
        f"- Seed: {exam['seed']}",
    ]
    for n in exam["solver"]["notes"]:
        lines.append(f"- {n}")
    if p["review_required_questions"]:
        lines += ["", f"**{len(p['review_required_questions'])} question(s) are REVIEW_REQUIRED:** " + ", ".join(f"`{x}`" for x in p["review_required_questions"])]
    lines.append("")
    return "\n".join(lines)


def analysis_report_markdown(workflow: Dict[str, Any]) -> str:
    """Workflow-level report from a dict of real counts gathered by the caller."""
    w = workflow
    lines = [
        "# ExamDNA Analysis Report",
        "",
        "## Workflow counts",
        "",
        "| Stage | Count |",
        "| --- | --- |",
    ]
    for key, label in (
        ("source_documents", "Source documents analysed"),
        ("extracted_questions", "Questions extracted"),
        ("genomes_complete", "Genomes complete"),
        ("mutation_specs", "Mutation specs planned"),
        ("candidates", "Candidates generated"),
        ("passed", "Candidates PASS"),
        ("review_required", "Candidates REVIEW_REQUIRED"),
        ("rejected", "Candidates rejected (FAIL)"),
        ("compiled_questions", "Questions in compiled exam"),
    ):
        if key in w:
            lines.append(f"| {label} | {w[key]} |")
    lines.append("")
    if w.get("deviations"):
        lines += ["## Deviations from requested targets", ""] + [f"- {d}" for d in w["deviations"]] + [""]
    if w.get("limitations"):
        lines += ["## Known limitations", ""] + [f"- {d}" for d in w["limitations"]] + [""]
    return "\n".join(lines)
