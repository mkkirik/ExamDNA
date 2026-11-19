# Evaluation: ExamDNA vs. unstructured generation

## What can be claimed

ExamDNA's outputs carry *observable* structure that an unstructured "write a similar exam" prompt does not guarantee. `examdna evaluate` measures these properties on any two artifacts:

- questions with all required fields (text, marks, topic, type, objectives, answer)
- requested vs. actual total marks; compliance
- section-mark distribution distance (TV) from the configured or blueprint sections
- distinct explicit learning objectives
- questions with lineage resolving to a source question
- surface-duplicate pairs; near-verbatim copies of source questions
- numeric solutions recomputed by the engine
- validation failures identified

No claim is made that ExamDNA produces better learning outcomes, more valid assessments, or more accurate difficulty. That would require empirical studies with students and expert raters.

## Demonstration (synthetic data)

`tools/run_demo.py` writes `examples/expected_outputs/demo_workspace/extras/baseline_comparison.md`. The baseline there is an **illustrative, hand-written fixture** (`examples/synthetic_inputs/baseline_naive_exam.json`) showing the format of an unstructured output. It is **not** the output of a measured model run, and the comparison is a demonstration of the tooling, not an experimental result.

## Protocol for a real paired experiment (results currently unavailable)

1. Fix a source set (≥ 3 papers with mark schemes, rights cleared) and a request ("30-mark exam, same structure").
2. **Baseline arm:** in a fresh conversation without the Skill, give the same sources and request with a fixed prompt. Save the output as `{"questions": [{"text", "marks", "section", "topic", "question_type", "learning_objectives", "answer"}]}` — transcribe only what the model actually produced; leave absent fields absent.
3. **ExamDNA arm:** same sources and request with the Skill enabled; keep the full workspace.
4. Repeat each arm *n* ≥ 10 times (new conversations) to capture variance; record model/version and date.
5. Run `examdna evaluate --baseline b_i.json --exam e_i/exam.json --config config.json --bank e_i/bank.json --validation e_i/validation_report.json --out r_i.json` for each pair.
6. Additionally have two independent subject experts blind-rate a random sample of questions from both arms for correctness, clarity and alignment to objectives; report inter-rater agreement.
7. Report per-metric distributions (median, IQR) across runs, not single runs; publish raw files.

Until such runs are performed and published, the experimental comparison is **unavailable**.
