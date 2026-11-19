# Changelog

All notable changes are documented here. The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-11-20

First release.

### Added
- Agent Skill `examdna` with `SKILL.md`, references (extraction, genome annotation, mutation operators, candidate format, compile config, communication incl. Turkish) and templates.
- Deterministic engine (`examdna` package, Python 3.9+ standard library only):
  - normalization of JSON / CSV / Markdown / text sources, optional PDF text extraction; provenance per field; prompt-injection flags;
  - Exam DNA analyzer with evidence IDs, uncertainty levels and a documented heuristic difficulty model;
  - question genome schema 0.1.0 with reasoning DAG analysis and genome comparison;
  - nine mutation operators with contracts, deterministic planner, variant planning, multi-generation lineage, mutation-distance profiles, duplicate detection and diversity selection;
  - validation engine (schema, structure, marking, safe exact recomputation, SI dimensional analysis, domain, constraints, uniqueness, invariants, copy detection);
  - constraint-aware exam compiler with infeasibility diagnosis and seeded reproducibility;
  - renderers for student paper (Markdown, A4 HTML), answer key, marking guide and reports (English/Turkish labels);
  - observable-property evaluation against a baseline;
  - deterministic Skill packaging and archive verification;
  - CLI (`ingest`, `analyze`, `genome`, `compare`, `operators`, `mutation-plan`, `validate`, `compile`, `render`, `report`, `lineage`, `evaluate`, `prepare`, `finish`, `package`, `verify-package`, `schema`, `extract-text`).
- Original synthetic physics dataset (3 papers, mark scheme, syllabus, notes, annotations, candidates incl. deliberately invalid ones, conflict config) and committed demo outputs.
- 110 automated tests; GitHub Actions workflow for Linux, macOS and Windows.
