"""ExamDNA command-line interface.

The CLI performs deterministic processing only. It never writes questions or
makes semantic judgements: those steps are done by the agent (Claude) and
handed over as JSON. Run ``python -m examdna.cli --help``.

Exit codes: 0 success · 1 input/validation error · 2 compilation infeasible.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .utilities.io import InputError, read_json_file, write_json, write_text


def _print(obj) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=True) + "\n")


def _csv(value: Optional[str]) -> Optional[List[str]]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else None


def _genomes(path: str):
    doc = read_json_file(path)
    return doc["genomes"] if isinstance(doc, dict) and "genomes" in doc else doc


# ------------------------------------------------------------------ commands
def cmd_ingest(a):
    from .extraction.loaders import load_source
    from .extraction.normalize import merge_banks

    banks = [load_source(p, subject=a.subject, document=a.document if len(a.inputs) == 1 else None) for p in a.inputs]
    bank = banks[0] if len(banks) == 1 else merge_banks(banks)
    write_json(a.out, bank)
    rep = bank["normalization_report"]
    _print({"out": a.out, "questions": rep["question_count"], "issues": len(rep["issues"]), "missing_marks": len(rep["missing_marks"]), "security_flagged": rep["security_flagged"]})


def cmd_extract_text(a):
    from .extraction.loaders import extract_pdf_text
    from .utilities.io import read_text_file

    text = extract_pdf_text(a.input) if a.input.lower().endswith(".pdf") else read_text_file(a.input)
    write_text(a.out, text)
    _print({"out": a.out, "characters": len(text)})


def cmd_genome(a):
    from .genome import build_genomes

    bank = read_json_file(a.bank)
    ann = read_json_file(a.annotations) if a.annotations else None
    doc = build_genomes(bank, ann)
    write_json(a.out, doc)
    _print({"out": a.out, **doc["report"]})
    return 1 if doc["report"]["errors"] else 0


def cmd_analyze(a):
    from .fingerprint import analyze_bank
    from .reporting import dna_report_markdown

    bank = read_json_file(a.bank)
    genomes = _genomes(a.genomes) if a.genomes else None
    dna = analyze_bank(bank, genomes)
    write_json(a.out, dna)
    if a.report:
        write_text(a.report, dna_report_markdown(dna))
    _print({"out": a.out, "papers": dna["source_set"]["paper_count"], "questions": dna["source_set"]["question_count"], "evidence_level": dna["uncertainty"]["evidence_level"], "notes": dna["uncertainty"]["notes"]})


def cmd_compare(a):
    from .genome import compare_genomes
    from .mutation.properties import full_text

    genomes = {g["question_id"]: g for g in _genomes(a.genomes)}
    for qid in (a.a, a.b):
        if qid not in genomes:
            raise InputError(f"no genome for {qid}")
    texts = (None, None)
    if a.bank:
        qs = {q["id"]: q for q in read_json_file(a.bank)["questions"]}
        texts = (full_text(qs[a.a]), full_text(qs[a.b])) if a.a in qs and a.b in qs else (None, None)
    _print(compare_genomes(genomes[a.a], genomes[a.b], *texts))


def cmd_operators(a):
    from .mutation import list_contracts

    contracts = list_contracts()
    if a.json:
        _print(contracts)
    else:
        for c in contracts:
            sys.stdout.write(f"{c['id']:<17} {c['name']:<28} modes={','.join(c['modes'])}\n  preserve: {', '.join(c['preserve'])}\n  must change: {', '.join(c['must_change'])}\n")


def cmd_plan(a):
    from .mutation import plan_mutations, plan_variants

    bank = read_json_file(a.bank)
    genomes = _genomes(a.genomes)
    if a.variants:
        if not a.question:
            raise InputError("--variants requires --question")
        plan = plan_variants(bank, genomes, a.question, a.variants, mode=a.mode or "exploratory", seed=a.seed, difficulty_direction=a.direction)
    else:
        plan = plan_mutations(
            bank,
            genomes,
            question_ids=_csv(a.questions),
            operators=_csv(a.operators),
            mode=a.mode or "balanced",
            per_question=a.per_question,
            seed=a.seed,
            difficulty_direction=a.direction,
        )
    write_json(a.out, plan)
    _print({"out": a.out, "plan_id": plan["plan_id"], "specs": len(plan["specs"]), "operators": sorted({s["operator"] for s in plan["specs"]}), "skipped": plan["skipped"][:10], "notes": plan["notes"]})


def cmd_validate(a):
    from .reporting import validation_summary_markdown
    from .validation import apply_states, validate_bank, validate_candidates

    bank = read_json_file(a.bank)
    if a.candidates:
        if not (a.plan and a.genomes):
            raise InputError("--candidates requires --plan and --genomes")
        doc = read_json_file(a.candidates)
        candidates = doc.get("candidates", doc) if isinstance(doc, dict) else doc
        report, pool = validate_candidates(candidates, read_json_file(a.plan), bank, _genomes(a.genomes))
        if a.pool:
            write_json(a.pool, pool)
    else:
        report = validate_bank(bank)
        if a.pool:
            write_json(a.pool, apply_states(bank, report))
    write_json(a.out, report)
    if a.summary:
        write_text(a.summary, validation_summary_markdown(report))
    _print({"out": a.out, **report["summary"]})


def cmd_compile(a):
    from .compiler import CompilationInfeasible, compile_exam

    pool = read_json_file(a.pool)
    config = read_json_file(a.config)
    if a.seed is not None:
        config["seed"] = a.seed
    dna = read_json_file(a.dna) if a.dna else None
    genomes = _genomes(a.genomes) if a.genomes else None
    try:
        exam = compile_exam(pool, config, dna, genomes)
    except CompilationInfeasible as exc:
        if a.diagnosis:
            write_json(a.diagnosis, exc.diagnosis)
        _print({"status": "infeasible", **exc.diagnosis})
        return 2
    write_json(a.out, exam)
    _print({"status": "compiled", "out": a.out, "exam_id": exam["exam_id"], "questions": exam["question_count"], "total_marks": exam["total_marks"], "exhaustive": exam["solver"]["exhaustive"], "review_required": exam["properties"]["review_required_questions"]})


def cmd_render(a):
    from .reporting import answer_key_markdown, exam_html, exam_markdown, marking_guide_markdown

    exam = read_json_file(a.exam)
    if a.lang:
        exam["language"] = a.lang
    out = Path(a.out_dir)
    files = {"exam.md": exam_markdown(exam), "exam.html": exam_html(exam), "answer_key.md": answer_key_markdown(exam), "marking_guide.md": marking_guide_markdown(exam)}
    for name, text in files.items():
        write_text(out / name, text)
    written = [str(out / n) for n in files]
    if a.pdf:
        written.append(_try_pdf(out / "exam.html", out / "exam.pdf"))
    _print({"written": written})


def _try_pdf(html_path: Path, pdf_path: Path) -> str:
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError:
        return "PDF skipped: optional 'weasyprint' not installed. Open exam.html and use Print → Save as PDF."
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    return str(pdf_path)


def cmd_report(a):
    from .mutation import build_lineage
    from .reporting import comparison_report_markdown, dna_report_markdown, lineage_report_markdown, validation_summary_markdown

    if a.kind == "dna":
        text = dna_report_markdown(read_json_file(a.dna))
    elif a.kind == "validation":
        text = validation_summary_markdown(read_json_file(a.report))
    elif a.kind == "lineage":
        qs = read_json_file(a.bank)["questions"] + (read_json_file(a.pool)["questions"] if a.pool else [])
        text = lineage_report_markdown(build_lineage(qs), read_json_file(a.exam) if a.exam else None)
    else:
        text = comparison_report_markdown(read_json_file(a.exam), read_json_file(a.dna) if a.dna else None)
    write_text(a.out, text)
    _print({"out": a.out})


def cmd_lineage(a):
    from .mutation import build_lineage, render_tree

    qs = read_json_file(a.bank)["questions"] + (read_json_file(a.pool)["questions"] if a.pool else [])
    lin = build_lineage(qs)
    if a.out:
        write_json(a.out, lin)
    sys.stdout.write(render_tree(lin))
    return 0 if lin["valid"] else 1


def cmd_evaluate(a):
    from .evaluation import compare, comparison_markdown

    result = compare(
        read_json_file(a.baseline),
        read_json_file(a.exam),
        read_json_file(a.config),
        source_bank=read_json_file(a.bank) if a.bank else None,
        validation_report=read_json_file(a.validation) if a.validation else None,
    )
    write_json(a.out, result)
    if a.markdown:
        write_text(a.markdown, comparison_markdown(result))
    _print({"out": a.out})


def cmd_package(a):
    from .packaging import build

    _print(build(Path(a.out) if a.out else None, verify=not a.no_verify))


def cmd_verify_package(a):
    from .packaging import verify_archive

    _print(verify_archive(Path(a.archive)))


def cmd_schema(a):
    from .models.schema import SCHEMA_NAMES, load_schema

    if a.name == "list":
        _print(SCHEMA_NAMES)
    else:
        _print(load_schema(a.name))


def cmd_prepare(a):
    from .workflow import prepare

    _print(prepare(a.workspace, mode=a.mode, per_question=a.per_question, seed=a.seed, operators=_csv(a.operators), questions=_csv(a.questions), difficulty_direction=a.direction))


def cmd_finish(a):
    from .workflow import finish

    result = finish(a.workspace, output_dir=a.output_dir, seed=a.seed)
    _print(result)
    return 2 if result["status"] == "infeasible" else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="examdna", description="ExamDNA deterministic engine. Semantic steps are performed by the agent and passed in as JSON.")
    p.add_argument("--version", action="version", version=f"examdna {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("ingest", help="normalize JSON/CSV/Markdown/text (or PDF with pypdf) sources into a question bank")
    s.add_argument("inputs", nargs="+")
    s.add_argument("--out", required=True)
    s.add_argument("--subject")
    s.add_argument("--document", help="document name to record (single input only)")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("extract-text", help="extract plain text from a PDF (optional pypdf) or text file")
    s.add_argument("input")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_extract_text)

    s = sub.add_parser("genome", help="build question genomes from a bank plus optional agent annotations")
    s.add_argument("--bank", required=True)
    s.add_argument("--annotations")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_genome)

    s = sub.add_parser("analyze", help="compute the Exam DNA profile of the source papers")
    s.add_argument("--bank", required=True)
    s.add_argument("--genomes")
    s.add_argument("--out", required=True)
    s.add_argument("--report", help="also write a Markdown report")
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("compare", help="compare two genomes dimension by dimension")
    s.add_argument("--genomes", required=True)
    s.add_argument("--a", required=True)
    s.add_argument("--b", required=True)
    s.add_argument("--bank", help="bank, to include surface-text similarity")
    s.set_defaults(func=cmd_compare)

    s = sub.add_parser("operators", help="list mutation operator contracts")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_operators)

    s = sub.add_parser("mutation-plan", help="create deterministic mutation specifications")
    s.add_argument("--bank", required=True)
    s.add_argument("--genomes", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--mode", choices=["conservative", "balanced", "exploratory"])
    s.add_argument("--operators", help="comma-separated operator ids")
    s.add_argument("--questions", help="comma-separated question ids")
    s.add_argument("--per-question", type=int, default=2)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--direction", choices=["up", "down"], default="up", help="difficulty operator direction")
    s.add_argument("--variants", type=int, help="plan N structurally different variants of --question")
    s.add_argument("--question")
    s.set_defaults(func=cmd_plan)

    s = sub.add_parser("validate", help="validate mutation candidates, or a question bank on its own")
    s.add_argument("--bank", required=True)
    s.add_argument("--candidates")
    s.add_argument("--plan")
    s.add_argument("--genomes")
    s.add_argument("--out", required=True)
    s.add_argument("--pool", help="write accepted questions (PASS + flagged REVIEW_REQUIRED) here")
    s.add_argument("--summary", help="also write a Markdown summary")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("compile", help="assemble an exam from a validated pool")
    s.add_argument("--pool", required=True)
    s.add_argument("--config", required=True)
    s.add_argument("--dna")
    s.add_argument("--genomes")
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int)
    s.add_argument("--diagnosis", help="where to write the infeasibility diagnosis")
    s.set_defaults(func=cmd_compile)

    s = sub.add_parser("render", help="render exam.json to Markdown, HTML, answer key and marking guide")
    s.add_argument("--exam", required=True)
    s.add_argument("--out-dir", required=True)
    s.add_argument("--lang", choices=["en", "tr"])
    s.add_argument("--pdf", action="store_true", help="also try PDF (needs optional weasyprint)")
    s.set_defaults(func=cmd_render)

    s = sub.add_parser("report", help="write a Markdown report")
    s.add_argument("kind", choices=["dna", "validation", "lineage", "compare"])
    s.add_argument("--dna")
    s.add_argument("--report")
    s.add_argument("--bank")
    s.add_argument("--pool")
    s.add_argument("--exam")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("lineage", help="build and print question lineage")
    s.add_argument("--bank", required=True)
    s.add_argument("--pool")
    s.add_argument("--out")
    s.set_defaults(func=cmd_lineage)

    s = sub.add_parser("evaluate", help="compare observable properties of a baseline exam and an ExamDNA exam")
    s.add_argument("--baseline", required=True)
    s.add_argument("--exam", required=True)
    s.add_argument("--config", required=True)
    s.add_argument("--bank")
    s.add_argument("--validation")
    s.add_argument("--out", required=True)
    s.add_argument("--markdown")
    s.set_defaults(func=cmd_evaluate)

    s = sub.add_parser("package", help="build the self-contained Skill zip (from a source checkout)")
    s.add_argument("--out")
    s.add_argument("--no-verify", action="store_true")
    s.set_defaults(func=cmd_package)

    s = sub.add_parser("verify-package", help="verify a Skill zip")
    s.add_argument("archive")
    s.set_defaults(func=cmd_verify_package)

    s = sub.add_parser("schema", help="print a JSON schema ('list' to list names)")
    s.add_argument("name")
    s.set_defaults(func=cmd_schema)

    s = sub.add_parser("prepare", help="workspace step 1: genomes + Exam DNA + mutation plan")
    s.add_argument("--workspace", required=True)
    s.add_argument("--mode", choices=["conservative", "balanced", "exploratory"], default="balanced")
    s.add_argument("--per-question", type=int, default=2)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--operators")
    s.add_argument("--questions")
    s.add_argument("--direction", choices=["up", "down"], default="up")
    s.set_defaults(func=cmd_prepare)

    s = sub.add_parser("finish", help="workspace step 2: validate candidates, compile, render, report")
    s.add_argument("--workspace", required=True)
    s.add_argument("--output-dir")
    s.add_argument("--seed", type=int)
    s.set_defaults(func=cmd_finish)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = args.func(args)
    except (InputError, ValueError, KeyError) as exc:
        sys.stderr.write(f"examdna: error: {exc}\n")
        return 1
    return int(code or 0)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
